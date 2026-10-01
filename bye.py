def welcome(name: str = "訪客") -> str:
    return f"歡迎光臨！很高興見到您，{name}！祝您有美好的一天！"


def main():
    print("=== 歡迎訊息系統 ===")
    try:
        name = input("請輸入您的姓名（直接按 Enter 使用預設）: ").strip()
        if not name:
            name = "訪客"
    except EOFError:
        name = "訪客"

    print(welcome(name))


if __name__ == "__main__":
    main()
