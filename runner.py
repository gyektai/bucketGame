import time
from utility_local import *

# I like the simplicity haha
def sleep(s):
    time.sleep(s)

# simulate a full run of the game with two accounts betting
def full_run_local():
    print("creating ...")
    appID = local_create(0)
    sleep(5)
    print("funding ...")
    local_fund_contract(appID)
    sleep(5)
    print("opting ...")
    local_optin(appID, 1)
    local_optin(appID, 2)
    sleep(5)
    print("calling 1 ...")
    local_call(appID, 1, 100000, 1)
    sleep(5)
    print("calling 2 ...")
    local_call(appID, 2, 120000, 2)


def call_local(appID):
    local_call(appID, 1, 100000, 1)


if __name__ == "__main__":
    #full_run_local()
    print(get_local_accounts())
    #call_local(48)
    #local_call(78, 2, 10000, 1)

    # manually keep track of application ids for ease of testing and deleting
    # ids = []
    # [local_delete(id, 0) for id in ids]
