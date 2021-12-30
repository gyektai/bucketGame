from algosdk import *
from algosdk.logic import get_application_address
from algosdk.v2client import algod
from algosdk.v2client.models import DryrunSource, DryrunRequest
from algosdk.future.transaction import *
import base64
import os
from algosdk import mnemonic
from algosdk import transaction
from sandbox import get_accounts
from txn_manager import waitForTransaction

# for local docker, can change for mainnet and testnet
# will not do that here for security
token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
url = "http://localhost:4001"

client = algod.AlgodClient(token, url)

print("how often is this called?")
# create a contract from the bucketGameProgram and send it
def local_create(acctNum):
    creator_addr, creator_pk = get_accounts()[acctNum]

    path = os.path.dirname(os.path.abspath(__file__))

    approval = open(os.path.join(path,'bucketGameProgram.teal')).read()
    app_result = client.compile(approval)
    app_bytes = base64.b64decode(app_result['result'])

    clear = open(os.path.join(path,'clearBucketGame.teal')).read()
    clear_result = client.compile(clear)
    clear_bytes = base64.b64decode(clear_result['result'])

    g_schema = StateSchema(5,0)
    l_schema = StateSchema(3,0)

    txn = ApplicationCreateTxn(
        sender=creator_addr,
        approval_program=app_bytes,
        clear_program=clear_bytes,
        global_schema=g_schema,
        local_schema=l_schema,
        sp=client.suggested_params(),
        on_complete=future.transaction.OnComplete.NoOpOC,
    )
    #print("Account: \n", client.account_info(creator_addr)["amount"])
    signedTxn = txn.sign(creator_pk)

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    assert response.applicationIndex is not None and response.applicationIndex > 0
    print("Application Index: {}".format(response.applicationIndex))
    return response.applicationIndex

def get_local_accounts():
    return get_accounts()
# send funds to the contract at appID
# usually just used to initially fund the contract
def local_fund_contract(appID):
    sender1, sender1_pk = get_accounts()[0]
    app_addr = get_application_address(appID)
    #print(app_addr)
    fund_sc = PaymentTxn(
        sender=sender1,
        receiver=app_addr,
        sp=client.suggested_params(),
        amt=100000,
    )
    stxn = fund_sc.sign(sender1_pk)
    tx_id = client.send_transaction(stxn)
    wait_for_confirmation(client, tx_id) 
    print("Funded at txn {}".format(tx_id))

def local_call(appID, acct, bet_size, side):
    app_addr = get_application_address(appID)
    caller, caller_pk = get_accounts()[acct]
    args = [side]

    txn_to_sc = PaymentTxn(
        sender=caller,
        receiver=app_addr,
        sp=client.suggested_params(),
        amt=bet_size,
    )
    txn_sc_to_recs = ApplicationCallTxn(
        sender=caller,
        index=appID,
        on_complete=future.transaction.OnComplete.NoOpOC,
        app_args=args,
        sp=client.suggested_params(),
    )

    group_id = transaction.calculate_group_id([txn_to_sc, txn_sc_to_recs])
    #print("================= GROUP : \n", group_id)
    txn_to_sc.group = group_id
    txn_sc_to_recs.group = group_id

    stxn = txn_to_sc.sign(caller_pk)
    scall = txn_sc_to_recs.sign(caller_pk)

    signed_group = [stxn, scall]
    tx_id = client.send_transactions(signed_group)

    #print("Account 1 \n", client.account_info(my_nft_addr)["amount"])
    wait_for_confirmation(client, tx_id)
    #print("Account 1 \n", client.account_info(my_nft_addr)["amount"]) 
    print("Bet placed on {}".format(side))
    #info = client.application_info(appID)
    #print(info)

def local_optin(appID, acctNum):
    sender, pk = get_accounts()[acctNum]
    txn = ApplicationOptInTxn(
        sender=sender,
        sp=client.suggested_params(),
        index=appID,
    )
    stxn = txn.sign(pk)
    tx_id = client.send_transaction(stxn)
    waitForTransaction(client, tx_id)
    print("Account {} opted in".format(sender))

def local_claim(appID, acctNum):
    caller, pk = get_accounts()[acctNum]
    print("before claim {}".format(client.account_info(caller)["amount"]))
    claim_call = ApplicationCallTxn(
        sender=caller,
        index=appID,
        on_complete=future.transaction.OnComplete.NoOpOC,
        sp=client.suggested_params(),
    )
    stxn = claim_call.sign(pk)
    tx_id = client.send_transaction(stxn)
    waitForTransaction(client, tx_id)
    print("after claim {}".format(client.account_info(caller)["amount"]))


def local_closeout(appID, acctNum):
    pass

def local_delete(appID, acctNum):
    caller, pk = get_accounts()[acctNum]
    delete_txn = ApplicationDeleteTxn(
        sender=caller,
        index=appID,
        sp=client.suggested_params(),
    )
    stxn = delete_txn.sign(pk)
    tx_id = client.send_transaction(stxn)
    waitForTransaction(client, tx_id)
    print("Deleted {}".format(appID))


if __name__ == "__main__":
    local_create()
