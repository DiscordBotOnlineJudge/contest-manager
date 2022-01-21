import time
import discord
import os
import subprocess
import math
import dns
import asyncio
from pymongo import MongoClient
from datetime import datetime
import pytz

def current_time():
    tz = pytz.timezone("America/New_York")
    return datetime.now(tz).strftime("%Y %m %d %H %M %S")

def all_equal(a, b):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True

def greater_equal(x, y, i):
    if i == 5:
        return x[5] >= y[5]
    if x[i] > y[i]:
        return True
    elif x[i] < y[i]:
        return False
    else:
        return greater_equal(x, y, i + 1)

def compString(a, b):
    a = list(map(int, a.split()))
    b = list(map(int, b.split()))
    return greater_equal(a, b, 0)

def date(a, b, c):
    x = list(map(int, a.split()))
    y = list(map(int, b.split()))
    u = list(map(int, c.split()))
    return (greater_equal(u, x, 0) and greater_equal(y, u, 0))

def compare(t1, t2):
    a = list(map(int, t1.split()))
    b = list(map(int, t2.split()))

    if a[0] != b[0] or a[1] != b[1] or a[2] != b[2]:
        return 999999 # Incorrect date

    total = (b[3] - a[3]) * 3600 + (b[4] - a[4]) * 60 + (b[5] - a[5])
    return total