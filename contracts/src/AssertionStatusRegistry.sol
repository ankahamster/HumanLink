// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IAssertionStatusRegistry {
    function revokeAssertion(bytes32 assertionHash) external;

    function isRevoked(bytes32 assertionHash) external view returns (bool);

    event AssertionRevoked(bytes32 indexed assertionHash, uint256 timestamp);
}

/**
 * @title AssertionStatusRegistry
 * @notice Tracks assertion revocation and optionally anchors audit summaries
 * for high-risk operations.
 * @dev The contract intentionally stores only digests and metadata hashes.
 * Raw assertions, biometric material, and private keys must stay off-chain.
 */
contract AssertionStatusRegistry is IAssertionStatusRegistry {
    error NotAuthorized();
    error EmptyAssertionHash();
    error AssertionAlreadyRevoked(bytes32 assertionHash);
    error AssertionAlreadyAnchored(bytes32 assertionHash);

    struct AssertionAuditInput {
        bytes32 assertionHash;
        bytes32 assertionIdHash;
        bytes32 deviceDidHash;
        bytes32 requiredIssuerDidHash;
        bytes32 actionHash;
        bytes32 nonceHash;
        bytes32 originHash;
        bytes32 verificationMethodHash;
        bytes32 signedHash;
        bytes32 sensorSerialHash;
        uint16 matchScore;
        uint64 createdAt;
        string protocolVersion;
    }

    struct AssertionAuditRecord {
        bool exists;
        bool revoked;
        bytes32 assertionIdHash;
        bytes32 deviceDidHash;
        bytes32 requiredIssuerDidHash;
        bytes32 actionHash;
        bytes32 nonceHash;
        bytes32 originHash;
        bytes32 verificationMethodHash;
        bytes32 signedHash;
        bytes32 sensorSerialHash;
        uint16 matchScore;
        uint64 createdAt;
        uint64 anchoredAt;
        uint64 revokedAt;
        string protocolVersion;
    }

    event AssertionAuditRecorded(
        bytes32 indexed assertionHash,
        bytes32 indexed deviceDidHash,
        bytes32 indexed actionHash,
        uint16 matchScore,
        uint64 createdAt,
        string protocolVersion
    );

    event RecorderUpdated(address indexed recorder, bool allowed);

    address public owner;
    mapping(address => bool) public recorders;
    mapping(bytes32 => AssertionAuditRecord) private _records;

    constructor(address initialOwner) {
        owner = initialOwner == address(0) ? msg.sender : initialOwner;
        recorders[owner] = true;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotAuthorized();
        _;
    }

    modifier onlyRecorder() {
        if (!recorders[msg.sender]) revert NotAuthorized();
        _;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "new owner is zero");
        owner = newOwner;
        recorders[newOwner] = true;
    }

    function setRecorder(address recorder, bool allowed) external onlyOwner {
        require(recorder != address(0), "recorder is zero");
        recorders[recorder] = allowed;
        emit RecorderUpdated(recorder, allowed);
    }

    function recordAssertionAudit(AssertionAuditInput calldata input) external onlyRecorder {
        if (input.assertionHash == bytes32(0)) revert EmptyAssertionHash();
        if (_records[input.assertionHash].exists) {
            revert AssertionAlreadyAnchored(input.assertionHash);
        }

        _records[input.assertionHash] = AssertionAuditRecord({
            exists: true,
            revoked: false,
            assertionIdHash: input.assertionIdHash,
            deviceDidHash: input.deviceDidHash,
            requiredIssuerDidHash: input.requiredIssuerDidHash,
            actionHash: input.actionHash,
            nonceHash: input.nonceHash,
            originHash: input.originHash,
            verificationMethodHash: input.verificationMethodHash,
            signedHash: input.signedHash,
            sensorSerialHash: input.sensorSerialHash,
            matchScore: input.matchScore,
            createdAt: input.createdAt,
            anchoredAt: uint64(block.timestamp),
            revokedAt: 0,
            protocolVersion: input.protocolVersion
        });

        emit AssertionAuditRecorded(
            input.assertionHash,
            input.deviceDidHash,
            input.actionHash,
            input.matchScore,
            input.createdAt,
            input.protocolVersion
        );
    }

    function revokeAssertion(bytes32 assertionHash) external onlyRecorder {
        if (assertionHash == bytes32(0)) revert EmptyAssertionHash();

        AssertionAuditRecord storage record = _records[assertionHash];
        if (record.revoked) revert AssertionAlreadyRevoked(assertionHash);

        if (!record.exists) {
            record.exists = true;
            record.anchoredAt = uint64(block.timestamp);
        }

        record.revoked = true;
        record.revokedAt = uint64(block.timestamp);

        emit AssertionRevoked(assertionHash, block.timestamp);
    }

    function isRevoked(bytes32 assertionHash) external view returns (bool) {
        return _records[assertionHash].revoked;
    }

    function hasAuditRecord(bytes32 assertionHash) external view returns (bool) {
        return _records[assertionHash].exists;
    }

    function getAssertionRecord(bytes32 assertionHash)
        external
        view
        returns (AssertionAuditRecord memory)
    {
        return _records[assertionHash];
    }
}
