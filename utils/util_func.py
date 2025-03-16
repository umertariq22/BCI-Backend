import math,random


def generate_otp(length=6):
    digits = "0123456789"
    otp = ""
    for i in range(length):
        otp += digits[math.floor(random.random() * 10)]
    return otp
