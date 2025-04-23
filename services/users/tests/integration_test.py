import uuid
import pytest
from ..src.users import Users
from shared_models.users.delete_user import DeleteUserRequest
from shared_models.users.create_user import CreateUserRequest, CreateUserResponse
from shared_models.users import User as UserSharedModel
from shared_models.users.deposit import DepositRequest
from shared_models.users.withdraw import WithdrawRequest
from shared_models.users.get_balance import GetBalanceRequest, GetBalanceResponse
from shared_models.users.errors import (
    UserNotFoundError,
    InsufficientFundsError
)
from database import BalanceHistory
from database.models.balance_history import OperationType
import asyncio
from shared_models.instruments.errors import InstrumentNotFoundError
from database import User, Instrument, Balance


@pytest.mark.asyncio
async def test_user_lifecycle_with_balances(ctx: dict):
    # 1. Create user
    create_response: CreateUserResponse = await Users.create_user(ctx, CreateUserRequest(name="Full Lifecycle User"))
    user_id = create_response.user.id
    
    # 2. Create instrument
    instrument = await Instrument.create(ticker="USD", name="US Dollar")
    
    # 3. Deposit funds
    deposit_request = DepositRequest(user_id=user_id, ticker="USD", amount=500)
    await Users.deposit(ctx, deposit_request)
    
    # 4. Verify balance after deposit
    get_balance_request = GetBalanceRequest(user_id=user_id)
    balance_response: GetBalanceResponse = await Users.get_balance(ctx, get_balance_request)
    assert balance_response.root[instrument.ticker] == 500
    
    # 5. Withdraw funds
    withdraw_request = WithdrawRequest(user_id=user_id, ticker="USD", amount=300)
    await Users.withdraw(ctx, withdraw_request)
    
    # 6. Verify balance after withdrawal
    balance_withdrawal: GetBalanceResponse = await Users.get_balance(ctx, get_balance_request)
    assert balance_withdrawal.root[instrument.ticker] == 200
    
    # 7. Try to withdraw more than available (should fail)
    with pytest.raises(InsufficientFundsError):
        bad_withdraw_request = WithdrawRequest(user_id=user_id, ticker="USD", amount=300)
        await Users.withdraw(ctx, bad_withdraw_request)
    
    # 8. Verify balance didn't change after failed withdrawal
    balance_failed_withdrawal: GetBalanceResponse = await Users.get_balance(ctx, get_balance_request)
    assert balance_failed_withdrawal.root[instrument.ticker] == 200


@pytest.mark.asyncio
async def test_multiple_instruments_operations(ctx: dict):
    # 1. Create user
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Multi Instrument User"))).user
    
    # 2. Create multiple instruments
    usd = await Instrument.create(ticker="USD", name="US Dollar")
    eur = await Instrument.create(ticker="EUR", name="Euro")
    gbp = await Instrument.create(ticker="GBP", name="British Pound")
    
    # 3. Deposit to multiple currencies
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=usd.ticker, amount=1000))
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=eur.ticker, amount=500))
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=gbp.ticker, amount=300))
    
    # 4. Verify all balances
    balance_response: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert balance_response.root[usd.ticker] == 1000
    assert balance_response.root[eur.ticker] == 500
    assert balance_response.root[gbp.ticker] == 300
    
    # 5. Make transfers between currencies (withdraw from one, deposit to another)
    await Users.withdraw(ctx, WithdrawRequest(user_id=user.id, ticker=usd.ticker, amount=200))
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=eur.ticker, amount=200))
    
    # 6. Verify new balances
    new_balance_response: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert new_balance_response.root[usd.ticker] == 800
    assert new_balance_response.root[eur.ticker] == 700
    assert new_balance_response.root[gbp.ticker] == 300


@pytest.mark.asyncio
async def test_error_handling_scenarios(ctx: dict):
    # 1. Try operations with non-existent user
    with pytest.raises(UserNotFoundError):
        await Users.get_balance(ctx, GetBalanceRequest(user_id=uuid.uuid4()))
    
    with pytest.raises(UserNotFoundError):
        await Users.deposit(ctx, DepositRequest(user_id=uuid.uuid4(), ticker="USD", amount=100))
    
    # 2. Create real user but try invalid operations
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Error Handling User"))).user
    
    with pytest.raises(InstrumentNotFoundError):
        await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker="XYZ", amount=100))
    
    with pytest.raises(InstrumentNotFoundError):
        await Users.withdraw(ctx, WithdrawRequest(user_id=user.id, ticker="USD", amount=100))
    
    # 3. Create instrument and test insufficient funds after partial withdrawal
    await Instrument.create(ticker="USD", name="US Dollar")
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker="USD", amount=50))
    
    with pytest.raises(InsufficientFundsError):
        await Users.withdraw(ctx, WithdrawRequest(user_id=user.id, ticker="USD", amount=100))


@pytest.mark.asyncio
async def test_user_deletion_with_balances(ctx: dict):
    # 1. Create user with balances
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Delete User"))).user
    usd = await Instrument.create(ticker="USD", name="US Dollar")
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=usd.ticker, amount=1000))
    
    # 2. Delete user
    await Users.delete_user(ctx, DeleteUserRequest(id=user.id))
    
    # 3. Verify all related data is deleted
    assert await User.get_or_none(id=user.id) is None
    assert await Balance.filter(user_id=user.id).count() == 0
    assert await BalanceHistory.filter(user_id=user.id).count() == 0
    
    # 4. Verify instrument still exists (should not be deleted with user)
    assert await Instrument.get_or_none(ticker=usd.ticker) is not None


@pytest.mark.asyncio
async def test_concurrent_operations(ctx: dict):
    # 1. Create user and instrument
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Concurrent User"))).user
    instrument = await Instrument.create(ticker="USD", name="US Dollar")
    
    # 2. Define deposit task
    async def deposit_task(amount):
        await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=instrument.ticker, amount=amount))
    
    # 3. Run multiple deposits concurrently
    tasks = [deposit_task(100) for _ in range(100)]
    await asyncio.gather(*tasks)
    
    # 4. Verify final balance
    balance_response: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert balance_response.root[instrument.ticker] == 10000


@pytest.mark.asyncio
async def test_high_volume_transactions(ctx: dict):
    # 1. Create user and instrument
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="High Volume User"))).user
    usd = await Instrument.create(ticker="USD", name="Dollar")
    
    # 2. Execute high volume transactions
    for i in range(1, 101):
        await Users.deposit(ctx, DepositRequest(
            user_id=user.id,
            ticker=usd.ticker,
            amount=i
        ))
        
        if i % 10 == 0:
            await Users.withdraw(ctx, WithdrawRequest(
                user_id=user.id,
                ticker=usd.ticker,
                amount=5
            ))
    
    # 3. Check final balance
    expected_balance = sum(range(1, 101)) - (5 * 10)
    balance: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert balance.root[usd.ticker] == expected_balance
    
    # 4. Check balance history
    deposit_count = await BalanceHistory.filter(
        user_id=user.id,
        operation_type=OperationType.DEPOSIT
    ).count()
        
    withdraw_count = await BalanceHistory.filter(
        user_id=user.id,
        operation_type=OperationType.WITHDRAW
    ).count()
        
    assert deposit_count == 100
    assert withdraw_count == 10
    

@pytest.mark.asyncio
async def test_balance_consistency_after_errors(ctx: dict):
    # 1. Create user and instrument, and deposit initial amount
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Consistency User"))).user
    usd = await Instrument.create(ticker="USD", name="Dollar")
    await Users.deposit(ctx, DepositRequest(user_id=user.id, ticker=usd.ticker, amount=100))
    
    initial_balance: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    
    # 2. Try to withdraw more than available (should raise error)
    with pytest.raises(InsufficientFundsError):
        await Users.withdraw(ctx, WithdrawRequest(
            user_id=user.id,
            ticker=usd.ticker,
            amount=200
        ))
    
    # 3. Check that balance remains unchanged
    current_balance: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert current_balance.root[usd.ticker] == initial_balance.root[usd.ticker]
    
    # 4. Try to deposit into a non-existent instrument (should raise error)
    with pytest.raises(InstrumentNotFoundError):
        await Users.deposit(ctx, DepositRequest(
            user_id=user.id,
            ticker="XYZ",
            amount=50
        ))
    
    # 5. Check that balance remains unchanged
    current_balance = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    assert current_balance.root[usd.ticker] == initial_balance.root[usd.ticker]

@pytest.mark.asyncio
async def test_user_operations_with_multiple_instruments(ctx: dict):
    # 1. Create user
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Multi Instrument User"))).user
    
    # 2. Create multiple instruments
    currencies = [
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
        ("JPY", "Japanese Yen")
    ]
    
    for ticker, name in currencies:
        await Instrument.create(ticker=ticker, name=name)
    
    # 3. Perform multiple operations
    operations = [
        ("USD", 500, "deposit"),
        ("EUR", 300, "deposit"),
        ("USD", 100, "withdraw"),
        ("GBP", 200, "deposit"),
        ("EUR", 50, "withdraw"),
        ("JPY", 10000, "deposit")
    ]
    
    for ticker, amount, op_type in operations:
        if op_type == "deposit":
            await Users.deposit(ctx, DepositRequest(
                user_id=user.id,
                ticker=ticker,
                amount=amount
            ))
        else:
            await Users.withdraw(ctx, WithdrawRequest(
                user_id=user.id,
                ticker=ticker,
                amount=amount
            ))
    
    # 4. Check final balances
    final_balances: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    
    assert final_balances.root["USD"] == 400
    assert final_balances.root["EUR"] == 250
    assert final_balances.root["GBP"] == 200
    assert final_balances.root["JPY"] == 10000
    assert len(final_balances.root) == 4, "Unexpected instruments found in balance response"

@pytest.mark.asyncio
async def test_concurrent_balance_updates(ctx: dict):
    user: UserSharedModel = (await Users.create_user(ctx, CreateUserRequest(name="Concurrent User"))).user
    instrument = await Instrument.create(ticker="XRP", name="Ripple")
    
    async def modify_balance(amount):
        await Users.deposit(ctx, DepositRequest(
            user_id=user.id,
            ticker=instrument.ticker,
            amount=amount
        ))
        await asyncio.sleep(0.01)
    
    tasks = [modify_balance(1) for _ in range(50)]
    await asyncio.gather(*tasks)
    
    balance: GetBalanceResponse = await Users.get_balance(ctx, GetBalanceRequest(user_id=user.id))
    user_model = await User.get(id=user.id)
    assert balance.root["XRP"] == 50
    assert await BalanceHistory.filter(user=user_model, instrument=instrument).count() == 50, "Balance history count mismatch"
    assert await Balance.filter(user=user_model, instrument=instrument).count() == 1, "Balance count mismatch"
    assert len(balance.root) == 1, "Unexpected instruments found in balance response"