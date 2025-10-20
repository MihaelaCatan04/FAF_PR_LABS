from counters.test_naive_counter import test_naive_counter
from counters.test_safe_counter import test_safe_counter

def counter_main():
    test_naive_counter()
    test_safe_counter()
    

if __name__ == '__main__':
    counter_main()