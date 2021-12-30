from pyteal import *
import os

def approval_program():

    # initialize variables to make code easier to read
    sender = Txn.sender()
    creator = Global.creator_address()
    args = Txn.application_args
    contract_addr = Global.current_application_address()
    asset_in_play = App.globalGet(Bytes("Asset"))
    asset_in_array = args[0]

    my_addr = "EKWUQAIM5JFDQAUDLU5NV3TLYR3EQLMHXOZ6G5KBQSSNG63V6KEOBY7WDI" # local deployment

    bucket_chosen = Btoi(args[0])
    a_amt = App.globalGet(Bytes("A"))
    b_amt = App.globalGet(Bytes("B"))
    algo_bet_amt = Gtxn[0].amount()
    asa_bet_amt = Gtxn[0].asset_amount()
    sponsor_withdrew = App.globalGet(Bytes("SponsorWithdrew"))


    a_wagered = App.localGet(sender, Bytes("A"))
    b_wagered = App.localGet(sender, Bytes("B"))
    

    current_time = Global.latest_timestamp()
    start_time = App.globalGet(Bytes("StartTime"))
    end_time = start_time + Int(1000) # diff num for deployment, endtime always measured as x seconds after start time
    closing_time = end_time + Int(30) # should be 86400 for a day after
    in_game = current_time >= start_time and current_time < end_time
    in_payout = current_time >= end_time
    sponsor_can_withdraw = current_time >= closing_time
    can_delete = current_time >= closing_time + Int(1000)


    # initialize global variables
    # StartTime and EndTime will be used more later
    handle_creation = Seq(
        App.globalPut(Bytes("StartTime"), current_time), # game starts immediately now. Why not?
        App.globalPut(Bytes("A"), Int(0)),
        App.globalPut(Bytes("B"), Int(0)),
        App.globalPut(Bytes("Asset"), Btoi(args[0])),
        App.globalPut(Bytes("SponsorWithdrew"), Int(0)),
        App.localPut(Int(0), Bytes("IsSponsor"), Int(1)),
        Return(Int(1))
    )

    # set initial local variables to 0 for opt in
    # have to change to make sure people send in enough algos to cover minimum
    # algo requirement for the smart contract
    handle_optin = Seq(
        App.localPut(Int(0), Bytes("A"), Int(0)),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        App.localPut(Int(0), Bytes("IsSponsor"), Int(0)),
        Return(Int(1))
    )

    # always can closeout participation
    handle_closeout = Return(Int(1))

    # can't update
    handle_updateapp = Reject()

    # only can delete if everything's over
    handle_deleteapp = If(And(can_delete, sender == my_addr), Approve(), Reject())

    # add's the bet amount to global A variable
    algo_make_a_bet = Seq(
        App.globalPut(Bytes("A"), a_amt + algo_bet_amt),
        App.localPut(Int(0), Bytes("A"), a_wagered + algo_bet_amt),
        Int(1)
    )

    # add's the bet amount to global B variable
    algo_make_b_bet = Seq(
        App.globalPut(Bytes("B"), b_amt + algo_bet_amt),
        App.localPut(Int(0), Bytes("B"), b_wagered + algo_bet_amt),
        Int(1)
    )

    # add's the bet amount to global A variable
    asa_make_a_bet = Seq(
        App.globalPut(Bytes("A"), a_amt + asa_bet_amt),
        App.localPut(Int(0), Bytes("A"), a_wagered + asa_bet_amt),
        Int(1)
    )

    # add's the bet amount to global B variable
    asa_make_b_bet = Seq(
        App.globalPut(Bytes("B"), b_amt + asa_bet_amt),
        App.localPut(Int(0), Bytes("B"), b_wagered + asa_bet_amt),
        Int(1)
    )

    # approve the creator doing whatever, and send args[0] algos to creator
    algo_handle_sponsor_withdrawal = Seq(
        Assert(sponsor_can_withdraw),
        Assert(sponsor_withdrew == Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: creator,
                TxnField.amount: (Balance(contract_addr) - MinimumBalance(contract_addr)) / Int(5) * Int(4),
            }),
        InnerTxnBuilder.Submit(),
        App.globalPut(Bytes("SponsorWithdrew"), Int(1)),
        Int(1)
    )

    algo_handle_my_withdrawal = Seq(
        Assert(sponsor_withdrew),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: my_addr,
                TxnField.amount: (Balance(contract_addr) - MinimumBalance(contract_addr)),
            }),
        InnerTxnBuilder.Submit(),
        Int(1)
    )

    # approve the creator doing whatever, and send args[0] algos to creator
    asa_handle_sponsor_withdrawal = Seq(
        Assert(sponsor_can_withdraw),
        Assert(sponsor_withdrew == Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransferTxn,
                TxnField.index: asset_in_play,
                TxnField.receiver: creator,
                TxnField.amount: AssetHolding.balance(contract_addr, asset_in_array).value() / Int(5) * Int(4),
            }),
        InnerTxnBuilder.Submit(),
        App.globalPut(Bytes("SponsorWithdrew"), Int(1)),
        Int(1)
    )

    asa_handle_my_withdrawal = Seq(
        Assert(sponsor_withdrew),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransferTxn,
                TxnField.index: asset_in_play,
                TxnField.receiver: my_addr,
                TxnField.amount: AssetHolding.balance(contract_addr, asset_in_array).value(),
            }),
        InnerTxnBuilder.Submit(),
        Int(1)
    )

    # create transaction to pay out winnings to A betters if A wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    algo_a_payout = Seq(
        Assert(a_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered * Int(2) - Int(1000), # for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("A"), Int(0)),
        Int(1)
    )
    # create transaction to pay out winnings to B betters if B wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    algo_b_payout = Seq(
        Assert(b_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: b_wagered * Int(2) - Int(1000), # for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("B"), Int(0)),
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
    asa_a_payout = Seq(
        Assert(a_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransferTxn,
                TxnField.index: asset_in_play,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered * Int(2), # no fee for assets
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("A"), Int(0)),
        Int(1)
    )
    # create transaction to pay out winnings to B betters if B wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    asa_b_payout = Seq(
        Assert(b_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransferTxn,
                TxnField.index: asset_in_play,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered * Int(2), # no fee for assets
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        Int(1)
    )

    # returns funds if there is a tie
    # sets both local states to 0 for no double payouts
    # transactions fees not dealt with properly
    asa_equal_payout = Seq(
        Assert(a_wagered + b_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransferTxn,
                TxnField.index: asset_in_play,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered + b_wagered,
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), Bytes("A"), Int(0)),
        App.localPut(Int(0), Bytes("B"), Int(0)),
        Int(1)
    )

    # make sure first transaction was payment to the contract account
    # set the bet to the side in the args array
    algo_play = Seq(
        Assert(Gtxn[0].receiver() == contract_addr),
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(sender != creator),
        Cond(
            [bucket_chosen == Int(1), algo_make_a_bet],
            [bucket_chosen == Int(2), algo_make_b_bet],
        )
    )

    # decide which side won and make the payout 
    algo_payout = Cond(
        [sender == creator, algo_handle_sponsor_withdrawal],
        [sender == my_addr, algo_handle_my_withdrawal],
        [a_amt < b_amt, algo_a_payout],
        [a_amt > b_amt, algo_b_payout],
        [a_amt == b_amt, algo_equal_payout],
    )

    # decide which side won and make the payout 
    asa_payout = Cond(
        [sender == creator, asa_handle_sponsor_withdrawal],
        [sender == my_addr, asa_handle_my_withdrawal],
        [a_amt < b_amt, asa_a_payout],
        [a_amt > b_amt, asa_b_payout],
        [a_amt == b_amt, asa_equal_payout],
    )

    # make sure first transaction was payment to the contract account
    # set the bet to the side in the args array
    asa_play = Seq(
        Assert(Gtxn[0].receiver() == contract_addr),
        Assert(Gtxn[0].type_enum() == TxnType.AssetTransferTxn),
        Assert(Gtxn[0].index == asset_in_play),
        Assert(sender != creator),
        Cond(
            [bucket_chosen == Int(1), asa_make_a_bet],
            [bucket_chosen == Int(2), asa_make_b_bet],
        )
    )
    
    # for application calls, if betting is taking place, then in game
    # otherwise if it's too late then let people withdraw
    algo_noop = Cond(
        [in_game, algo_play],
        [in_payout, algo_payout],
    )

    asa_noop = Seq(
        Assert(asset_in_play == asset_in_array),
        Cond(
            [in_game, asa_play],
            [in_payout, asa_payout]
        ))


    handle_noop = If(asset_in_play == Int(0), algo_noop, asa_noop)
    



    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
        [Txn.on_completion() == OnComplete.NoOp, Return(handle_noop)]
    )

    return compileTeal(program, mode=Mode.Application, version=5)

def clear_state_program():
    program = Return(Int(1))
    return compileTeal(program, mode=Mode.Application, version=5)

if __name__ == "__main__":
    path = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(path,"bucketGameProgram.teal"), "w") as f:
        f.write(approval_program())

    with open(os.path.join(path,"clearBucketGame.teal"), "w") as f:
        f.write(clear_state_program())