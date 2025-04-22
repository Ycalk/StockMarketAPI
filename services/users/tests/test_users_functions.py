import pytest
from ..src.users import Users
from shared_models.users.create_user import CreateUserRequest, CreateUserResponse
from shared_models.users.delete_user import DeleteUserRequest, DeleteUserResponse
from shared_models.users.get_user import GetUserRequest, GetUserResponse
from shared_models.users.deposit import DepositRequest
from shared_models.users.withdraw import WithdrawRequest
from shared_models.users.get_balance import GetBalanceRequest, GetBalanceResponse
from shared_models.users.errors import (
    UserNotFoundError,
    InsufficientFundsError,
)
from shared_models.instruments.errors import InstrumentNotFoundError
from database import User, Balance, Instrument, BalanceHistory
from database.models.balance_history import OperationType
import uuid


@pytest.mark.asyncio
async def test_create_user(ctx: dict):
    user_name = "Test User"
    request = CreateUserRequest(name=user_name)

    response: CreateUserResponse = await Users.create_user(ctx, request)

    assert isinstance(response, CreateUserResponse)
    assert response.user.name == user_name

    user = await User.get_or_none(id=response.user.id)
    assert user is not None
    assert user.name == response.user.name
    assert user.id == response.user.id


@pytest.mark.asyncio
async def test_delete_user(ctx: dict):
    create_request = CreateUserRequest(name="User to Delete")
    create_response: CreateUserResponse = await Users.create_user(ctx, create_request)

    delete_request = DeleteUserRequest(id=create_response.user.id)
    delete_response: DeleteUserResponse = await Users.delete_user(ctx, delete_request)

    assert isinstance(delete_response, DeleteUserResponse)
    assert delete_response.user.id == create_response.user.id

    user = await User.get_or_none(id=create_response.user.id)
    assert user is None


@pytest.mark.asyncio
async def test_get_user(ctx: dict):
    create_request = CreateUserRequest(name="Test Get User")
    create_response: CreateUserResponse = await Users.create_user(ctx, create_request)

    get_request = GetUserRequest(id=create_response.user.id)
    get_response: GetUserResponse = await Users.get_user(ctx, get_request)

    assert isinstance(get_response, GetUserResponse)
    assert get_response.user.id == create_response.user.id
    assert get_response.user.name == "Test Get User"


@pytest.mark.asyncio
async def test_deposit(ctx: dict):
    user = await User.create(name="Deposit User")
    instrument = await Instrument.create(ticker="ABC", name="Test Instrument")

    deposit_request = DepositRequest(
        user_id=user.id, ticker=instrument.ticker, amount=100
    )
    await Users.deposit(ctx, deposit_request)

    balance = await Balance.get_or_none(user=user, instrument=instrument)
    assert balance is not None
    assert balance.amount == 100

    history = await BalanceHistory.filter(user=user, instrument=instrument).first()
    assert history is not None
    assert history.amount == 100
    assert history.operation_type == OperationType.DEPOSIT


@pytest.mark.asyncio
async def test_withdraw(ctx: dict):
    user = await User.create(name="Withdraw User")
    instrument = await Instrument.create(ticker="ABC", name="Test Instrument")
    await Balance.create(user=user, instrument=instrument, amount=200)

    withdraw_request = WithdrawRequest(
        user_id=user.id, ticker=instrument.ticker, amount=50
    )
    await Users.withdraw(ctx, withdraw_request)

    balance = await Balance.get_or_none(user=user, instrument=instrument)
    assert balance is not None
    assert balance.amount == 150

    history = await BalanceHistory.filter(
        user=user, instrument=instrument, operation_type=OperationType.WITHDRAW
    ).first()
    assert history is not None
    assert history.amount == 50


@pytest.mark.asyncio
async def test_get_balance(ctx: dict):
    user = await User.create(name="Balance User")
    usd = await Instrument.create(ticker="USD", name="Dollar")
    eur = await Instrument.create(ticker="EUR", name="Euro")
    await Balance.create(user=user, instrument=usd, amount=100)
    await Balance.create(user=user, instrument=eur, amount=200)

    get_request = GetBalanceRequest(user_id=user.id)
    response: GetBalanceResponse = await Users.get_balance(ctx, get_request)

    assert isinstance(response, GetBalanceResponse)
    assert response.root["USD"] == 100
    assert response.root["EUR"] == 200


@pytest.mark.asyncio
async def test_delete_nonexistent_user(ctx: dict):
    with pytest.raises(UserNotFoundError):
        request = DeleteUserRequest(id=uuid.uuid4())
        await Users.delete_user(ctx, request)


@pytest.mark.asyncio
async def test_get_nonexistent_user(ctx: dict):
    with pytest.raises(UserNotFoundError):
        request = GetUserRequest(id=uuid.uuid4())
        await Users.get_user(ctx, request)


@pytest.mark.asyncio
async def test_deposit_to_nonexistent_user(ctx: dict):
    with pytest.raises(UserNotFoundError):
        request = DepositRequest(user_id=uuid.uuid4(), ticker="USD", amount=100)
        await Users.deposit(ctx, request)


@pytest.mark.asyncio
async def test_deposit_nonexistent_instrument(ctx: dict):
    user = await User.create(name="Test User")
    with pytest.raises(InstrumentNotFoundError):
        request = DepositRequest(user_id=user.id, ticker="AAA", amount=100)
        await Users.deposit(ctx, request)


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(ctx: dict):
    user = await User.create(name="Test User")
    instrument = await Instrument.create(ticker="USD", name="US Dollar")
    await Balance.create(user=user, instrument=instrument, amount=50)

    with pytest.raises(InsufficientFundsError):
        request = WithdrawRequest(user_id=user.id, ticker="USD", amount=100)
        await Users.withdraw(ctx, request)
