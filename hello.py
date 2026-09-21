def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def get_bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "體重過輕"
    elif 18.5 <= bmi < 24:
        return "正常範圍"
    elif 24 <= bmi < 27:
        return "過重"
    elif 27 <= bmi < 30:
        return "輕度肥胖"
    elif 30 <= bmi < 35:
        return "中度肥胖"
    else:
        return "重度肥胖"


def main():
    print("=== BMI 計算器 ===")
    try:
        height = float(input("請輸入身高 (公分): "))
        weight = float(input("請輸入體重 (公斤): "))

        if height <= 0 or weight <= 0:
            print("身高和體重必須大於 0！")
            return

        bmi = calculate_bmi(height, weight)
        category = get_bmi_category(bmi)

        print(f"\n您的 BMI 為: {bmi:.2f}")
        print(f"健康狀態評估: {category}")
    except ValueError:
        print("輸入格式錯誤，請輸入數值！")


if __name__ == "__main__":
    main()
