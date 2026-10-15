from operator import methodcaller
from collections import defaultdict
class TimeMap:

    def __init__(self):
        self.values = defaultdict(list)
        

    def set(self, key: str, value: str, timestamp: int) -> None:
        self.values[key].append((value, timestamp))
        

    def get(self, key: str, timestamp: int) -> str:
        values = self.values[key]
        res = ""
        l , r = 0 , len(values) - 1
        while l <= r :
            mid = (l + r) >> 1
            if values[mid][1] <= timestamp:
                l = mid + 1
                res = values[mid][0]
            else:
                r = mid - 1
        return res
        
        


# Your TimeMap object will be instantiated and called as such:
# obj = TimeMap()
# obj.set(key,value,timestamp)
# param_2 = obj.get(key,timestamp)
if __name__ == "__main__":
    ins1 = ["set","get","get","set","get","get"]
    ins2 = [["foo","bar",1],["foo",1],["foo",3],["foo","bar2",4],["foo",4],["foo",5]]
    timemap = TimeMap()
    for one, two in zip(ins1, ins2):
        methodcaller(one, *two)(timemap)
    print(timemap.values)
