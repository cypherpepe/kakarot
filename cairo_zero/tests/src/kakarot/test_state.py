import pytest
from eth_utils import keccak
from ethereum.shanghai.transactions import (
    TX_ACCESS_LIST_ADDRESS_COST,
    TX_ACCESS_LIST_STORAGE_KEY_COST,
)

from tests.utils.constants import ALL_PRECOMPILES, TRANSACTIONS
from tests.utils.helpers import flatten_tx_access_list, merge_access_list
from tests.utils.syscall_handler import SyscallHandler


class TestState:
    class TestInit:
        def test_should_return_state_with_default_dicts(self, cairo_run):
            cairo_run("test__init__should_return_state_with_default_dicts")

    class TestCopy:
        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_return_new_state_with_same_attributes(self, cairo_run):
            cairo_run("test__copy__should_return_new_state_with_same_attributes")

    class TestIsAccountAlive:
        @pytest.mark.parametrize(
            "nonce, code, balance_low, expected_result",
            (
                (0, [], 0, False),
                (1, [], 0, True),
                (0, [1], 0, True),
                (0, [], 1, True),
            ),
        )
        def test_should_return_true_when_existing_account_cached(
            self, cairo_run, nonce, code, balance_low, expected_result
        ):
            code_hash_bytes = keccak(bytes(code))
            code_hash = int.from_bytes(code_hash_bytes, "big")
            is_alive = cairo_run(
                "test__is_account_alive__account_alive_in_state",
                nonce=nonce,
                code=code,
                code_hash=code_hash,
                balance_low=balance_low,
            )
            assert is_alive == expected_result

        @SyscallHandler.patch("IAccount.bytecode", lambda *_: [1, [0x2]])
        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        @SyscallHandler.patch("IAccount.get_nonce", lambda *_: [1])
        @SyscallHandler.patch("Kakarot_evm_to_starknet_address", 0xABDE1, 0x1234)
        @SyscallHandler.patch("IAccount.get_code_hash", lambda *_: [0x1, 0x1])
        def test_should_return_true_when_existing_account_not_cached(self, cairo_run):
            cairo_run(
                "test__is_account_alive__account_alive_not_in_state",
            )

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 0])
        @SyscallHandler.patch("Kakarot_evm_to_starknet_address", 0xABDE1, 0)
        def test_should_return_false_when_not_in_state_nor_starknet(self, cairo_run):
            cairo_run("test__is_account_alive__account_not_alive_not_in_state")

    class TestIsAccountWarm:
        def test_should_return_true_when_account_in_state(self, cairo_run):
            cairo_run("test__is_account_warm__account_in_state")

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_return_false_when_account_not_state(self, cairo_run):
            cairo_run("test__is_account_warm__account_not_in_state")

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_warm_up_account(self, cairo_run):
            cairo_run("test__is_account_warm__warms_up_account")

    class TestIsStorageWarm:
        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_return_true_when_already_read(self, cairo_run):
            cairo_run("test__is_storage_warm__should_return_true_when_already_read")

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_return_true_when_already_written(self, cairo_run):
            cairo_run("test__is_storage_warm__should_return_true_when_already_written")

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_return_false_when_not_accessed(self, cairo_run):
            cairo_run("test__is_storage_warm__should_return_false_when_not_accessed")

    class TestCachePreaccessedAddresses:
        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        def test_should_cache_precompiles(self, cairo_run):
            state = cairo_run("test__cache_precompiles")
            assert [
                int(address, 16) for address in state["accounts"].keys()
            ] == ALL_PRECOMPILES

        @SyscallHandler.patch("IERC20.balanceOf", lambda *_: [0, 1])
        @pytest.mark.parametrize("transaction", TRANSACTIONS)
        def test_should_cache_access_list(self, cairo_run, transaction):
            access_list = transaction.get("accessList") or ()
            gas_cost, state = cairo_run(
                "test__cache_access_list",
                access_list=flatten_tx_access_list(access_list),
            )

            # count addresses key in access list, with duplicates
            assert gas_cost == TX_ACCESS_LIST_ADDRESS_COST * len(
                access_list
            ) + TX_ACCESS_LIST_STORAGE_KEY_COST * sum(
                len(x["storageKeys"]) for x in access_list
            )

            # check that all addresses and storage keys are in the state
            expected_result = merge_access_list(access_list)
            for address, storage_keys in expected_result.items():
                assert state["accounts"].get(address) is not None
                assert set(state["accounts"][address]["storage"].keys()) == storage_keys
                assert all(
                    state["accounts"][address]["storage"][key] is not None
                    for key in storage_keys
                )

    class TestCopyAccounts:
        def test_should_handle_null_pointers(self, cairo_run):
            cairo_run("test___copy_accounts__should_handle_null_pointers")
