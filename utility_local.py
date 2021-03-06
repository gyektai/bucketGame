from abc import get_cache_token
from algosdk import *
from algosdk.logic import get_application_address
from algosdk.v2client import algod
from algosdk.future.transaction import *
import base64
import os
from algosdk import mnemonic
from algosdk import transaction
from sandbox import get_accounts
from txn_manager import waitForTransaction



class AlgoRunner:
    def __init__(self, net):
        if net == 'local':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        elif net == 'test':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        elif net == 'main':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        else:
            raise ValueError   

    # create a contract from the bucketGameProgram and send it
    def create(self, acctNum):
        creator_addr, creator_pk = get_accounts()[acctNum]

        path = os.path.dirname(os.path.abspath(__file__))

        approval = open(os.path.join(path,'asaBucketProgram.teal')).read()
        app_result = self.client.compile(approval)
        app_bytes = base64.b64decode(app_result['result'])

        clear = open(os.path.join(path,'clearAsaBucketGame.teal')).read()
        clear_result = self.client.compile(clear)
        clear_bytes = base64.b64decode(clear_result['result'])

        g_schema = StateSchema(5,0)
        l_schema = StateSchema(3,0)

        txn = ApplicationCreateTxn(
            sender=creator_addr,
            approval_program=app_bytes,
            clear_program=clear_bytes,
            global_schema=g_schema,
            local_schema=l_schema,
            sp=self.client.suggested_params(),
            on_complete=future.transaction.OnComplete.NoOpOC,
            foreign_assets=[0]
        )
        #print("Account: \n", client.account_info(creator_addr)["amount"])
        signedTxn = txn.sign(creator_pk)

        self.client.send_transaction(signedTxn)

        response = waitForTransaction(self.client, signedTxn.get_txid())
        assert response.applicationIndex is not None and response.applicationIndex > 0
        print("Application Index: {}".format(response.applicationIndex))
        return response.applicationIndex

    def get_local_accounts(self):
        return get_accounts()
    # send funds to the contract at appID
    # usually just used to initially fund the contract
    def fund_contract(self, appID):
        sender1, sender1_pk = get_accounts()[0]
        app_addr = get_application_address(appID)
        #print(app_addr)
        fund_sc = PaymentTxn(
            sender=sender1,
            receiver=app_addr,
            sp=self.client.suggested_params(),
            amt=100000,
        )
        stxn = fund_sc.sign(sender1_pk)
        tx_id = self.client.send_transaction(stxn)
        wait_for_confirmation(self.client, tx_id) 
        print("Funded at txn {}".format(tx_id))

    def call(self, appID, acct, bet_size, side):
        app_addr = get_application_address(appID)
        caller, caller_pk = get_accounts()[acct]
        args = [side]

        txn_to_sc = PaymentTxn(
            sender=caller,
            receiver=app_addr,
            sp=self.client.suggested_params(),
            amt=bet_size,
        )
        sc_call = ApplicationCallTxn(
            sender=caller,
            index=appID,
            on_complete=future.transaction.OnComplete.NoOpOC,
            app_args=args,
            sp=self.client.suggested_params(),
        )

        group_id = transaction.calculate_group_id([txn_to_sc, sc_call])
        #print("================= GROUP : \n", group_id)
        txn_to_sc.group = group_id
        sc_call.group = group_id

        stxn = txn_to_sc.sign(caller_pk)
        scall = sc_call.sign(caller_pk)

        signed_group = [stxn, scall]
        tx_id = self.client.send_transactions(signed_group)

        #print("Account 1 \n", client.account_info(my_nft_addr)["amount"])
        #wait_for_confirmation(self.client, tx_id)
        #print("Account 1 \n", client.account_info(my_nft_addr)["amount"]) 
        print("Bet placed on {} by {}".format(side, acct))
        #info = client.application_info(appID)
        #print(info)

    def optin(self, appID, acctNum):
        sender, pk = get_accounts()[acctNum]
        txn = ApplicationOptInTxn(
            sender=sender,
            sp=self.client.suggested_params(),
            index=appID,
        )
        stxn = txn.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        print("Account {} opted in".format(sender))

    def claim(self, appID, acctNum):
        caller, pk = get_accounts()[acctNum]
        before_balance = self.client.account_info(caller)["amount"]
        #print("before claim {}".format(before_balance))
        claim_call = ApplicationCloseOutTxn(
            sender=caller,
            index=appID,
            sp=self.client.suggested_params(),
        )
        stxn = claim_call.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        after_balance = self.client.account_info(caller)["amount"]
        #print("after claim  {}".format(after_balance))
        print("{} difference for {}".format(after_balance - before_balance, acctNum))


    def closeout(self, appID, acctNum):
        pass

    def delete(self, appID, acctNum):
        caller, pk = get_accounts()[acctNum]
        bsb = self.client.account_info(caller)["amount"]
        bob = self.client.account_info(get_accounts()[0][0])["amount"]
        delete_txn = ApplicationDeleteTxn(
            sender=caller,
            index=appID,
            sp=self.client.suggested_params(),
            accounts=["EKWUQAIM5JFDQAUDLU5NV3TLYR3EQLMHXOZ6G5KBQSSNG63V6KEOBY7WDI"] # because my_acct is hardcoded
        )
        stxn = delete_txn.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        asb = self.client.account_info(caller)["amount"]
        aob = self.client.account_info(get_accounts()[0][0])["amount"]
        print("Ending \n {} paid to sponsor {} \n {} paid to owner {}".format(asb - bsb, acctNum, aob - bob, 0))

class AsaRunner:
    def __init__(self, net, asset):
        if net == 'local':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        elif net == 'test':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        elif net == 'main':
            token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            url = "http://localhost:4001"
            self.client = algod.AlgodClient(token, url)
        else:
            raise ValueError   
        self.assetID = asset
    # create a contract from the bucketGameProgram and send it
    def create(self, acctNum):
        creator_addr, creator_pk = get_accounts()[acctNum]

        path = os.path.dirname(os.path.abspath(__file__))

        approval = open(os.path.join(path,'asaBucketProgram.teal')).read()
        app_result = self.client.compile(approval)
        app_bytes = base64.b64decode(app_result['result'])

        clear = open(os.path.join(path,'clearAsaBucketGame.teal')).read()
        clear_result = self.client.compile(clear)
        clear_bytes = base64.b64decode(clear_result['result'])

        g_schema = StateSchema(4,0)
        l_schema = StateSchema(3,0)

        txn = ApplicationCreateTxn(
            sender=creator_addr,
            approval_program=app_bytes,
            clear_program=clear_bytes,
            global_schema=g_schema,
            local_schema=l_schema,
            sp=self.client.suggested_params(),
            on_complete=future.transaction.OnComplete.NoOpOC,
            foreign_assets=[self.assetID],
        )
        #print("Account: \n", client.account_info(creator_addr)["amount"])
        signedTxn = txn.sign(creator_pk)

        self.client.send_transaction(signedTxn)

        response = waitForTransaction(self.client, signedTxn.get_txid())
        assert response.applicationIndex is not None and response.applicationIndex > 0
        print("Application Index: {}".format(response.applicationIndex))

        # need sc to opt in to assetID
        app_addr = get_application_address(response.applicationIndex)


        return response.applicationIndex

    def get_local_accounts(self):
        return get_accounts()
    # send funds to the contract at appID
    # usually just used to initially fund the contract
    def fund_contract(self, appID):
        sender1, sender1_pk = get_accounts()[0]
        app_addr = get_application_address(appID)
        #print(app_addr)
        fund_sc = PaymentTxn(
            sender=sender1,
            receiver=app_addr,
            sp=self.client.suggested_params(),
            amt=1500000, #might be way too much
        )
        stxn = fund_sc.sign(sender1_pk)
        tx_id = self.client.send_transaction(stxn)
        wait_for_confirmation(self.client, tx_id) 
        print("Funded at txn {}".format(tx_id))
        self.sc_asa_optin(appID)

    def call(self, appID, acct, bet_size, side):
        app_addr = get_application_address(appID)
        caller, caller_pk = get_accounts()[acct]
        args = [side]

        txn_to_sc = AssetTransferTxn(
            sender=caller,
            receiver=app_addr,
            sp=self.client.suggested_params(),
            amt=bet_size,
            index=self.assetID,
        )
        sc_call = ApplicationCallTxn(
            sender=caller,
            index=appID,
            on_complete=future.transaction.OnComplete.NoOpOC,
            app_args=args,
            foreign_assets=[self.assetID],
            sp=self.client.suggested_params(),
        )

        group_id = transaction.calculate_group_id([txn_to_sc, sc_call])
        #print("================= GROUP : \n", group_id)
        txn_to_sc.group = group_id
        sc_call.group = group_id

        stxn = txn_to_sc.sign(caller_pk)
        scall = sc_call.sign(caller_pk)

        signed_group = [stxn, scall]
        tx_id = self.client.send_transactions(signed_group)

        #print("Account 1 \n", client.account_info(my_nft_addr)["amount"])
        wait_for_confirmation(self.client, tx_id)
        #print("Account 1 \n", client.account_info(my_nft_addr)["amount"]) 
        print("Bet placed on {}".format(side))
        #info = client.application_info(appID)
        #print(info)

    def optin(self, appID, acctNum):
        sender, pk = get_accounts()[acctNum]
        txn = ApplicationOptInTxn(
            sender=sender,
            sp=self.client.suggested_params(),
            index=appID,
        )
        stxn = txn.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        print("Account {} opted in".format(sender))

    def claim(self, appID, acctNum):
        caller, pk = get_accounts()[acctNum]
        before_balance = self.client.account_info(caller)['assets'][0]['amount']
        claim_call = ApplicationCloseOutTxn(
            sender=caller,
            index=appID,
            foreign_assets=[self.assetID],
            sp=self.client.suggested_params(),
        )
        stxn = claim_call.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        after_balance = self.client.account_info(caller)['assets'][0]['amount']
        print("difference {} for {}".format(after_balance - before_balance, acctNum))


    def delete(self, appID, acctNum):
        caller, pk = get_accounts()[acctNum]
        bsb = self.client.account_info(caller)['assets'][0]['amount']
        bob = self.client.account_info(get_accounts()[0][0])['assets'][0]['amount']
        delete_txn = ApplicationDeleteTxn(
            sender=caller,
            index=appID,
            sp=self.client.suggested_params(),
            accounts=["EKWUQAIM5JFDQAUDLU5NV3TLYR3EQLMHXOZ6G5KBQSSNG63V6KEOBY7WDI"],
            foreign_assets=[self.assetID]
        )
        stxn = delete_txn.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        asb = self.client.account_info(caller)['assets'][0]['amount']
        aob = self.client.account_info(get_accounts()[0][0])['assets'][0]['amount']
        print("Ending assets \n {} paid to sponsor {} \n {} paid to owner {}".format(asb - bsb, acctNum, aob - bob, 0))


    def create_asa(self, acctNum):
        caller, pk = get_accounts()[acctNum]
        create_txn = AssetCreateTxn(
            sender=caller,
            sp=self.client.suggested_params(),
            total=10000000000,
            decimals=0,
            default_frozen=False,
            manager="", reserve="", freeze="", clawback="",
            unit_name="TDRP",
            asset_name="Drops Test",
            url="",
        )
        stxn = create_txn.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        response = waitForTransaction(self.client, tx_id)
        print("Created TDRP with assetID of {}".format(response.assetIndex))
    
    # absolute garbage code here. Clean this up later. Still gonna commit it lol
    def transfer_asset(self):
        accts = get_accounts()
        sender, spk = accts[1]
        opter1, opk1 = accts[0]
        opter2, opk2 = accts[2]

        optIn = AssetTransferTxn(
            sender=opter1,
            amt=0,
            receiver=opter1,
            sp=self.client.suggested_params(),
            index=self.assetID
        )
        stxn = optIn.sign(opk1)
        tx_id = self.client.send_transaction(stxn)
        optIn = AssetTransferTxn(
            sender=opter2,
            amt=0,
            receiver=opter2,
            sp=self.client.suggested_params(),
            index=self.assetID
        )
        stxn = optIn.sign(opk2)
        tx_id = self.client.send_transaction(stxn)
        response = waitForTransaction(self.client, tx_id)

        transferTxn = AssetTransferTxn(
            sender=sender,
            amt=1000000000,
            receiver=get_accounts()[0][0],
            sp=self.client.suggested_params(),
            index=self.assetID
        )
        stxn = transferTxn.sign(spk)
        tx_id = self.client.send_transaction(stxn)
        response = waitForTransaction(self.client, tx_id)
        transferTxn = AssetTransferTxn(
            sender=sender,
            amt=1000000000,
            receiver=get_accounts()[2][0],
            sp=self.client.suggested_params(),
            index=self.assetID
        )
        stxn = transferTxn.sign(spk)
        tx_id = self.client.send_transaction(stxn)
        response = waitForTransaction(self.client, tx_id)
        print("Funded")

    def sc_asa_optin(self, appID):
        caller, pk = get_accounts()[1]
        claim_call = ApplicationCallTxn(
            sender=caller,
            index=appID,
            foreign_assets=[self.assetID],
            on_complete=future.transaction.OnComplete.NoOpOC,
            sp=self.client.suggested_params(),
        )
        stxn = claim_call.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        print("sc opted in to asset")

    # eh this is probably useless. Will remake later to be useful
    # might not be as garbage as that asset creation and transfer
    def local_hard_clear(self, appID, acctNum):
        caller, pk = get_accounts()[acctNum]
        clear_call = ApplicationClearStateTxn(
            sender=caller,
            index=appID,
            sp=self.client.suggested_params(),
        )
        stxn = clear_call.sign(pk)
        tx_id = self.client.send_transaction(stxn)
        waitForTransaction(self.client, tx_id)
        print("deleted {}".format(appID))
        
