// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DemoMerchant {
    event ServicePurchased(
        address indexed buyer,
        uint256 amountWei,
        string purpose,
        bytes32 indexed actionHash
    );

    error ZeroPayment();

    function purchase(string calldata purpose, bytes32 actionHash) external payable {
        if (msg.value == 0) {
            revert ZeroPayment();
        }

        emit ServicePurchased(msg.sender, msg.value, purpose, actionHash);
    }
}
