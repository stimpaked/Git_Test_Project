# 첫 번째 Git 테스트 파일
# 작성자: 마크
# 날짜: 2024-12-24

def greet(name):
    """인사하는 함수"""
    return f"안녕하세요, {name}님!"


def add(a, b):
    """두 숫자를 더하는 함수"""
    return a + b


if __name__ == "__main__":
    # 인사 테스트
    print(greet("마크"))
    
    # 계산 테스트
    result = add(10, 20)
    print(f"10 + 20 = {result}")
