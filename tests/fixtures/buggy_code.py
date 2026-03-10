def divide(a, b):
    return a / b  # bug : pas de verification si b == 0

def get_user(users, index):
    return users[index]  # bug : index peut etre hors limites

password = "admin123"  # securite : credential hardcode

def f(x):
    r = 0
    for i in range(x):
        r = r + i
    return r  # style : nommage peu clair
