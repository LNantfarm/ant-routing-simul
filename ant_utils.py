import time

def get_timestamp():
    t = round(time.time()*10) % 256
    return t

def lifespan(data):
    return (get_timestamp() - data.timestamp) % 256


def seed_bar(seed):
    return str(1 - int(seed[0])) + seed[1:]

def main():
    import random

    for _ in range(10):
        time.sleep(random.random()/4)
        print(get_timestamp())


if __name__ == "__main__":
    main()
