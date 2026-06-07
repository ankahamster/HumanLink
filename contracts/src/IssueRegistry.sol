// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IssueRegistry
 * @notice Implements the issuer registry role described in README / demo.
 * @dev The filename follows the requested IssueRegistry.sol naming, while the
 * contract semantics match the documented IssuerRegistry behavior.
 */
interface IIssueRegistry {
    /// @notice Register a new issuer device together with attestation metadata.
    function registerIssuer(
        bytes calldata pkIssuer,
        string calldata did,
        string calldata attestationHash
    ) external;

    /// @notice Return whether the issuer public key is currently valid.
    function isValidIssuer(bytes calldata pkIssuer) external view returns (bool);

    /// @notice Revoke an issuer record.
    function revokeIssuer(bytes32 issuerHash) external;

    event IssuerRegistered(bytes32 indexed issuerHash, string did);
    event IssuerRevoked(bytes32 indexed issuerHash, uint256 timestamp);
}

contract IssueRegistry is IIssueRegistry {
    error NotOwner();
    error EmptyPublicKey();
    error EmptyDID();
    error IssuerAlreadyRegistered(bytes32 issuerHash);
    error IssuerNotFound(bytes32 issuerHash);
    error IssuerAlreadyRevoked(bytes32 issuerHash);

    struct IssuerRecord {
        bytes publicKey;
        string did;
        string attestationHash;
        bool active;
        uint64 registeredAt;
        uint64 revokedAt;
    }

    address public owner;
    mapping(bytes32 => IssuerRecord) private _issuers;
    mapping(bytes32 => bytes32) private _issuerHashByDidHash;

    constructor(address initialOwner) {
        owner = initialOwner == address(0) ? msg.sender : initialOwner;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "new owner is zero");
        owner = newOwner;
    }

    function registerIssuer(
        bytes calldata pkIssuer,
        string calldata did,
        string calldata attestationHash
    ) external onlyOwner {
        if (pkIssuer.length == 0) revert EmptyPublicKey();
        if (bytes(did).length == 0) revert EmptyDID();

        bytes32 issuerHash = keccak256(pkIssuer);
        if (_issuers[issuerHash].registeredAt != 0) {
            revert IssuerAlreadyRegistered(issuerHash);
        }

        _issuers[issuerHash] = IssuerRecord({
            publicKey: pkIssuer,
            did: did,
            attestationHash: attestationHash,
            active: true,
            registeredAt: uint64(block.timestamp),
            revokedAt: 0
        });
        _issuerHashByDidHash[keccak256(bytes(did))] = issuerHash;

        emit IssuerRegistered(issuerHash, did);
    }

    function isValidIssuer(bytes calldata pkIssuer) external view returns (bool) {
        bytes32 issuerHash = keccak256(pkIssuer);
        IssuerRecord storage record = _issuers[issuerHash];
        return record.registeredAt != 0 && record.active;
    }

    function revokeIssuer(bytes32 issuerHash) external onlyOwner {
        IssuerRecord storage record = _issuers[issuerHash];
        if (record.registeredAt == 0) revert IssuerNotFound(issuerHash);
        if (!record.active) revert IssuerAlreadyRevoked(issuerHash);

        record.active = false;
        record.revokedAt = uint64(block.timestamp);

        emit IssuerRevoked(issuerHash, block.timestamp);
    }

    function getIssuer(bytes32 issuerHash) external view returns (IssuerRecord memory) {
        return _issuers[issuerHash];
    }

    function getIssuerHashByDid(string calldata did) external view returns (bytes32) {
        return _issuerHashByDidHash[keccak256(bytes(did))];
    }

    function issuerExists(bytes32 issuerHash) external view returns (bool) {
        return _issuers[issuerHash].registeredAt != 0;
    }
}
