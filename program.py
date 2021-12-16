from pyteal import *
import os

def approval_program():

    # initialize variables to make code easier to read
    sender = Txn.sender()
    creator = Global.creator_address()
    args = Txn.application_args
    contract_addr = Global.current_application_address()

    bucket_chosen = Btoi(args[0])
    a_amt = App.globalGet(Bytes("A"))
    b_amt = App.globalGet(Bytes("B"))
    bet_amt = Gtxn[0].amount()

    a_wagered = App.localGet(sender, Bytes("A"))
    b_wagered = App.localGet(sender, Bytes("B"))
    

    creation_time = App.globalGet(Bytes("CreationTime"))
    current_time = Global.latest_timestamp()
    start_time = creation_time + Int(60) # num should be diff for deployment
    end_time = start_time + Int(200) # diff num for deployment
    closing_time = end_time + Int(60) # should be 86400 for a day after
    in_game = current_time >= start_time and current_time < end_time
    in_payout = current_time >= end_time
    can_closeout = current_time >= closing_time

    # initialize global variables
    # StartTime and EndTime will be used more later
    handle_creation = Seq(
        App.globalPut(Bytes("CreationTime"), Global.latest_timestamp()),
        App.globalPut(Bytes("StartTime"), start_time), # int 1 is bad here. need time
        App.globalPut(Bytes("EndTime"), end_time), # int 1 is also bad here
        App.globalPut(Bytes("A"), Int(0)),
        App.globalPut(Bytes("B"), Int(0)),
        Return(Int(1))
    )

    # set initial local variables to 0 for opt in
    handle_optin = Seq(
        App.localPut(sender, Bytes("A"), Int(0)),
        App.localPut(sender, Bytes("B"), Int(0)),
        Return(Int(1))
    )

    # only can closeout after people have a long time to withdraw
    handle_closeout = If(can_closeout, Return(sender == creator), Reject())

    # can't update
    handle_updateapp = Reject()

    # only can delete if everything's over
    handle_deleteapp = If(can_closeout, Approve(), Reject())

    # add's the bet amount to global A variable
    make_a_bet = Seq(
        App.globalPut(Bytes("A"), a_amt + bet_amt),
        App.localPut(sender, Bytes("A"), a_wagered + bet_amt),
        Int(1)
    )

    # add's the bet amount to global B variable
    make_b_bet = Seq(
        App.globalPut(Bytes("B"), b_amt + bet_amt),
        App.localPut(sender, Bytes("B"), b_wagered + bet_amt),
        Int(1)
    )

    # create transaction to pay out winnings to A betters if A wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    a_payout = Seq(
        Assert(a_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered * Int(2) - Int(1000), # for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(sender, Bytes("A"), Int(0)),
        Int(1)
    )
    # create transaction to pay out winnings to B betters if B wins
    # set local state to 0 for no double payouts
    # transactions fees not dealt with properly
    b_payout = Seq(
        Assert(b_wagered > Int(0)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: b_wagered * Int(2) - Int(1000), # for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(sender, Bytes("B"), Int(0)),
        Int(1)
    )

    # returns funds if there is a tie
    # sets both local states to 0 for no double payouts
    # transactions fees not dealt with properly
    equal_payout = Seq(
        Assert(a_wagered + b_wagered > Int(1000)),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: sender,
                TxnField.amount: a_wagered + b_wagered - Int(1000), # less 1000 for fee
            }),
        InnerTxnBuilder.Submit(),
        App.localPut(sender, Bytes("A"), Int(0)),
        App.localPut(sender, Bytes("B"), Int(0)),
        Int(1)
    )

    # make sure first transaction was payment to the contract account
    # set the bet to the side in the args array
    play = Seq(
        Assert(Gtxn[0].receiver() == contract_addr),
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Cond(
            [bucket_chosen == Int(1), make_a_bet],
            [bucket_chosen == Int(2), make_b_bet],
        )
    )

    # decide which side won and make the payout 
    payout = Cond(
        [a_amt < b_amt, a_payout],
        [a_amt > b_amt, b_payout],
        [a_amt == b_amt, equal_payout],
    )
    
    # for application calls, if betting is taking place, then in game
    # otherwise if it's too late then let people withdraw
    handle_noop = Cond(
        [in_game, play],
        [in_payout, payout],
    )


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