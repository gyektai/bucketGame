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
    runner.call(appID, 2, 1200, 2)
    print("third call ...")
    runner.call(appID, 1, 1000, 2)
    runner.call(appID, 2, 1100, 1)


def call_local(runner, appID):
    runner.call(appID, 0, 100000, 1)

# ASA Drops id of 131
if __name__ == "__main__":
    #runner = AlgoRunner('local')
    runner = AsaRunner('local', 131)
    #print(runner.get_local_accounts())
    #runner.transfer_asset()
    full_run_local(runner)
    #call_local(runner, 144)

    #[runner.claim(230, n) for n in [0, 1, 2]]
    #print(runner.get_local_accounts())
    #call_local(runner, 107)
    #local_call(78, 2, 10000, 1)
    #runner.local_claim(107, 1)
    #print(runner.get_local_accounts()[0])


    # manually keep track of application ids for ease of testing and deleting
    #ids = [239] # maybe can't delete? sender != my_addr over there?
    #[runner.delete(id, 1) for id in ids]
