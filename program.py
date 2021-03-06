from pyteal import *
import os

def approval_program():

    # initialize variables to make code easier to read
    sender = Txn.sender()
    creator = Global.creator_address()
    args = Txn.application_args
    contract_addr = Global.current_application_address()
    asset_in_play = App.globalGet(Bytes("Asset"))
    asset_in_array = Txn.assets[0]
    in_algo_game = asset_in_play == Int(0)

    my_addr = Addr("EKWUQAIM5JFDQAUDLU5NV3TLYR3EQLMHXOZ6G5KBQSSNG63V6KEOBY7WDI") # local deployment

    bucket_chosen = Btoi(args[0])
    a_amt = App.globalGet(Bytes("A"))
    b_amt = App.globalGet(Bytes("B"))
    algo_bet_amt = Gtxn[0].amount()
    asa_bet_amt = Gtxn[0].asset_amount()


    a_wagered = App.localGet(Int(0), Bytes("A"))
    b_wagered = App.localGet(Int(0), Bytes("B"))
    

    current_time = Global.latest_timestamp()
    start_time = App.globalGet(Bytes("StartTime"))
    end_time = start_time + Int(1000) # diff num for deployment, endtime always measured as x seconds after start time

    in_game = current_time >= start_time and current_time < end_time
    in_payout = current_time >= end_time
    can_delete = current_time >= end_time + Int(1000)

    def getSideBytes(side): return If(side == Int(1), Bytes("A"), Bytes("B"))
    def getGlobalWagered(side): return If(side == Int(1), a_amt, b_amt)
    def getLocalWagered(side): return If(side == Int(1), a_wagered, b_wagered)


    # initialize global variables
    handle_creation = Seq(
        App.globalPut(Bytes("StartTime"), current_time), # game starts immediately on creation
        App.globalPut(Bytes("A"), Int(0)),
        App.globalPut(Bytes("B"), Int(0)),
        App.globalPut(Bytes("Asset"), asset_in_array),
        Return(Int(1))
    )

    # set initial local variables to 0 for opt in
    handle_optin = Seq(
        App.localPut(Int(0), Bytes("A"), Int(0)),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        Return(Int(1))
    )

    # can't update
    handle_updateapp = Reject()

    # payout what remains in the contract to sponsor 80% and me rest
    algo_handle_withdrawal = Seq(
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: creator,
                TxnField.amount: Balance(contract_addr) / Int(5) * Int(4),
            }),
        InnerTxnBuilder.Submit(),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.close_remainder_to: my_addr,
            }),
        InnerTxnBuilder.Submit(),
        Int(1)
    )
    
    contractAssetBalance = AssetHolding.balance(contract_addr, Txn.assets[0])
    contractAssetValue = Seq(
        contractAssetBalance,
        contractAssetBalance.value()
    )
    # payout what remains in the contract 80% to sponsor rest to me
    asa_handle_withdrawal = Seq(
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_in_play,
                TxnField.asset_receiver: creator,
                TxnField.asset_amount: contractAssetValue / Int(5) * Int(4),
            }),
        InnerTxnBuilder.Submit(),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_in_play,
                TxnField.asset_close_to: my_addr
            }),
        InnerTxnBuilder.Submit(),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.close_remainder_to: creator,
            }),
        InnerTxnBuilder.Submit(),

        Int(1)
    )

    # only can delete if everything's over
    handle_deleteapp = Return(Seq(
        Assert(can_delete),
        If(asset_in_play == Int(0),
            algo_handle_withdrawal,
            asa_handle_withdrawal
        )))

    # payout the won algos, twice the amount bet on the winning side
    def algo_payout(side):
        return Seq(
            Assert(getLocalWagered(side) > Int(0)),
            InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: sender,
                    TxnField.amount: getLocalWagered(side) * Int(2) - Int(1000), # -1000 for fee
                }),
            InnerTxnBuilder.Submit(),
            App.localPut(Int(0), getSideBytes(side), Int(0)),
            Int(1)
        )

    # returns funds if there is a tie
    # sets both local states to 0 for no double payouts
    # transactions fees not dealt with properly
    algo_equal_payout = Seq(
        Assert(a_wagered + b_wagered > Int(1000)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered + b_wagered - Int(1000), # less 1000 for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("A"), Int(0)),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        Int(1)
    )

    # create transaction to pay out winnings to A betters if A wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    def asa_payout(side):
        return Seq(
            Assert(getLocalWagered(side) > Int(0)),
            InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: asset_in_play,
                    TxnField.asset_receiver: sender,
                    TxnField.asset_amount: getLocalWagered(side) * Int(2), # no fee for assets
                }),
            InnerTxnBuilder.Submit(),
            App.localPut(Int(0), getSideBytes(side), Int(0)),
            Int(1)
        )

    # returns funds if there is a tie
    # sets both local states to 0 for no double payouts
    # transactions fees not dealt with properly
    asa_equal_payout = Seq(
        Assert(a_wagered + b_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_in_play,
                TxnField.asset_receiver: sender,
                TxnField.asset_amount: a_wagered + b_wagered,
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("A"), Int(0)),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        Int(1)
    )

    # decide which side won and make the payout in the proper asset
    handle_payout = Cond(
        [a_amt < b_amt, If(in_algo_game, 
            algo_payout(Int(1)), asa_payout(Int(1)))],
        [a_amt > b_amt, If(in_algo_game, 
            algo_payout(Int(2)), asa_payout(Int(2)))],
        [a_amt == b_amt, If(in_algo_game, 
            algo_equal_payout, asa_equal_payout)],
    )

    # payout the won amount and then opt out
    handle_closeout = Return(If(in_payout, handle_payout, Int(0)))

    # to call the proper amount vs asset_amount function
    bet_amt = If(in_algo_game, algo_bet_amt, asa_bet_amt)
    # add's the bet amount to the proper side globally and locally
    def make_bet(side):
        return Seq(
            App.globalPut(getSideBytes(side), getGlobalWagered(side) + bet_amt),
            App.localPut(Int(0), getSideBytes(side), getLocalWagered(side) +  bet_amt),
            Int(1)
    )

    # make sure first transaction was payment to the contract account
    # set the bet to the side in the args array
    algo_play = Seq(
        Assert(Gtxn[0].receiver() == contract_addr),
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(in_game),
        make_bet(bucket_chosen)
    )

    # opt this contract into the asa in play
    handle_asa_optin = Seq(
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_in_play,
                TxnField.asset_receiver: contract_addr,
                TxnField.asset_amount: Int(0),
            }),
        InnerTxnBuilder.Submit(),
        Int(1)
    )

    # make sure first transaction was payment to the contract account
    # set the bet to the side in the args array
    asa_play = Seq(
        Assert(Gtxn[0].asset_receiver() == contract_addr),
        Assert(Gtxn[0].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[0].xfer_asset() == asset_in_play),
        make_bet(bucket_chosen)
    )

    # to check if the contract is already opted into the asset
    asset_balance = AssetHolding.balance(contract_addr, asset_in_play)
    contract_opted = Seq(
        asset_balance,
        asset_balance.hasValue()
    )
    # make sure the contract is opted into the asset for the game
    # the first call to the contract should be in a gtxn with the contract
    # first getting funded
    # otherwise handle the bet being placed
    asa_noop = Seq(
        Assert(asset_in_play == asset_in_array),
        Assert(in_game),
        If(contract_opted, 
            asa_play, 
            handle_asa_optin))

    # different noops for if the game's for algo or asa
    handle_noop = Return(
        If(asset_in_play == Int(0), algo_play, asa_noop))
    
    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop]
    )

    return compileTeal(program, mode=Mode.Application, version=5)

def clear_state_program():
    program = Return(Int(1))
    return compileTeal(program, mode=Mode.Application, version=5)

if __name__ == "__main__":
    path = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(path,"asaBucketProgram.teal"), "w") as f:
        f.write(approval_program())

    with open(os.path.join(path,"clearAsaBucketGame.teal"), "w") as f:
        f.write(clear_state_program())