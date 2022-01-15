import time
from utility_local import AlgoRunner, AsaRunner

# I like the simplicity haha
def sleep(s):
    time.sleep(s)

# simulate a full run of the game with two accounts betting
def full_run_local(runner):
    print("creating ...")
    appID = runner.create(1)
    print("funding ...")
    runner.fund_contract(appID)
    print("opting ...")
    runner.optin(appID, 0)
    runner.optin(appID, 1)
    runner.optin(appID, 2)
    print("calling 1 ...")
    runner.call(appID=appID, acct=0, bet_size=1000, side=1)
    print("calling 2 ...")
    runner.call(appID, 1, 10000, 1)
    print("third call ...")
    runner.call(appID, 0, 12000, 1)
    runner.call(appID, 1, 1000, 2)
    runner.call(appID, 2, 40000, 2)
    sleep(5)
    print("round 2 calls ...")
    runner.call(appID, 2, 8000, 1)
    runner.call(appID, 0, 3000, 2)
    runner.call(appID, 1, 10000, 1)
    runner.call(appID, 0, 5000, 1)
    return appID


def call_local(runner, appID):
    runner.call(appID, 0, 100000, 1)

# ASA Drops id of 131
if __name__ == "__main__":
    #runner = AlgoRunner('local')
    #runner = AlgoRunner('local')
    runner = AsaRunner('local', 131)
    #print(runner.get_local_accounts())
    #runner.transfer_asset()
    appID = full_run_local(runner)
    sleep(90)
    [runner.claim(appID, acct) for acct in range(3)]
    sleep(100)
    runner.delete(appID, 1)



    # manually keep track of application ids for ease of testing and deleting
    #ids = [239, 252, 277, 307, 336, 490] # prob can't delete these
    # account 1 prob has 4 or 5 created assets...
    # 394, 426, 458 also created, but prob already deleted
    #[runner.delete(id, 1) for id in ids] 
    # ^ deprecated ince delete is for owner and sponsor payments
