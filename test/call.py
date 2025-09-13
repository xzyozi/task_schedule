
def main() :
    print(" call me python ")

    with open("test.txt" , "w") as f:
        f.write("test")
    print(" end process")

if __name__ == "__main__":
    print(" call main")
    main()