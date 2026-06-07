// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IUserDeviceRegistry {
    /// @notice Bind a device DID to a user hash in local or self-custodied flows.
    function bindDevice(bytes32 userIdHash, string calldata deviceDID) external;

    /// @notice Return the device DID bound to the user hash.
    function getDeviceDID(bytes32 userIdHash) external view returns (string memory);

    /// @notice Remove an existing user/device binding.
    function unbindDevice(bytes32 userIdHash) external;

    event DeviceBound(bytes32 indexed userIdHash, string deviceDID);
    event DeviceUnbound(bytes32 indexed userIdHash, uint256 timestamp);
}

contract UserDeviceRegistry is IUserDeviceRegistry {
    error NotAuthorized();
    error EmptyUserIdHash();
    error EmptyDeviceDID();
    error NoBinding(bytes32 userIdHash);

    struct DeviceBinding {
        string deviceDID;
        address controller;
        bool active;
        uint64 boundAt;
        uint64 updatedAt;
    }

    address public owner;
    mapping(bytes32 => DeviceBinding) private _bindings;

    constructor(address initialOwner) {
        owner = initialOwner == address(0) ? msg.sender : initialOwner;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotAuthorized();
        _;
    }

    modifier onlyBindingController(bytes32 userIdHash) {
        DeviceBinding storage binding = _bindings[userIdHash];
        if (
            msg.sender != owner &&
            binding.controller != address(0) &&
            msg.sender != binding.controller
        ) {
            revert NotAuthorized();
        }
        _;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "new owner is zero");
        owner = newOwner;
    }

    function bindDevice(bytes32 userIdHash, string calldata deviceDID)
        external
        onlyBindingController(userIdHash)
    {
        if (userIdHash == bytes32(0)) revert EmptyUserIdHash();
        if (bytes(deviceDID).length == 0) revert EmptyDeviceDID();

        DeviceBinding storage binding = _bindings[userIdHash];
        address controller = binding.controller == address(0) ? msg.sender : binding.controller;

        binding.deviceDID = deviceDID;
        binding.controller = controller;
        binding.active = true;

        uint64 nowTs = uint64(block.timestamp);
        if (binding.boundAt == 0) {
            binding.boundAt = nowTs;
        }
        binding.updatedAt = nowTs;

        emit DeviceBound(userIdHash, deviceDID);
    }

    function getDeviceDID(bytes32 userIdHash) external view returns (string memory) {
        DeviceBinding storage binding = _bindings[userIdHash];
        if (!binding.active) {
            return "";
        }
        return binding.deviceDID;
    }

    function unbindDevice(bytes32 userIdHash) external onlyBindingController(userIdHash) {
        DeviceBinding storage binding = _bindings[userIdHash];
        if (!binding.active) revert NoBinding(userIdHash);

        binding.active = false;
        binding.updatedAt = uint64(block.timestamp);

        emit DeviceUnbound(userIdHash, block.timestamp);
    }

    function getBinding(bytes32 userIdHash) external view returns (DeviceBinding memory) {
        return _bindings[userIdHash];
    }

    function bindingController(bytes32 userIdHash) external view returns (address) {
        return _bindings[userIdHash].controller;
    }
}
