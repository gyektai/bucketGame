import time
from utility_local import LocalRunnerAlgo, LocalRunnerAsa

# I like the simplicity haha
def sleep(s):
    time.sleep(s)

# simulate a full run of the game with two accounts betting
def full_run_local(runner):
    print("creating ...")
    appID = runner.local_create(0)
    #sleep(5)
    print("funding ...")
    runner.local_fund_contract(appID)
    #sleep(5)
    print("opting ...")
    runner.local_sc_optin(appID)
    runner.local_optin(appID, 1)
    runner.local_optin(appID, 2)
    runner.local_call(appID, 1, 0, 3)
    #sleep(5)
    print("calling 1 ...")
    runner.local_call(appID, 1, 100000, 1)
    #sleep(5)
    print("calling 2 ...")
    runner.local_call(appID, 2, 120000, 2)


def call_local(runner, appID):
    runner.local_call(appID, 1, 100000, 1)

# ASA Drops id of 131
if __name__ == "__main__":
    #runner = LocalRunnerAlgo()
    runner = LocalRunnerAsa(131)
    #runner.transfer_asset()
    full_run_local(runner)
    #call_local(runner, 144)

    #full_run_local_algo(runner, 0)
    #runner.local_claim(93, 0)
    #print(runner.get_local_accounts())
    #call_local(runner, 107)
    #local_call(78, 2, 10000, 1)
    #runner.local_claim(107, 1)
    #print(runner.get_local_accounts()[0])


    # manually keep track of application ids for ease of testing and deleting
    # ids = [93, 107, 132, 140, 144, 148, 150]
    # [local_delete(id, 0) for id in ids]
