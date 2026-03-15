r1_state = 0
r2_state = 0
r3_state = 0


def clock_r1(input_bit=0):
    """Сдвиг первого регистра (длина 19)"""
    global r1_state
    # Достаем нужные биты
    bit13 = (r1_state // (2 ** 13)) % 2
    bit16 = (r1_state // (2 ** 16)) % 2
    bit17 = (r1_state // (2 ** 17)) % 2
    bit18 = (r1_state // (2 ** 18)) % 2

    # Считаем новый бит
    feedback = (bit18 + bit17 + bit16 + bit13 + input_bit) % 2

    # Умножаем на 2, отрезаем лишнее
    r1_state = (r1_state * 2) % (2 ** 19)
    r1_state = r1_state + feedback


def clock_r2(input_bit=0):
    """Сдвиг второго регистра (длина 22)"""
    global r2_state
    bit20 = (r2_state // (2 ** 20)) % 2
    bit21 = (r2_state // (2 ** 21)) % 2

    feedback = (bit21 + bit20 + input_bit) % 2

    r2_state = (r2_state * 2) % (2 ** 22)
    r2_state = r2_state + feedback


def clock_r3(input_bit=0):
    """Сдвиг третьего регистра (длина 23)"""
    global r3_state
    bit7 = (r3_state // (2 ** 7)) % 2
    bit20 = (r3_state // (2 ** 20)) % 2
    bit21 = (r3_state // (2 ** 21)) % 2
    bit22 = (r3_state // (2 ** 22)) % 2

    feedback = (bit22 + bit21 + bit20 + bit7 + input_bit) % 2

    r3_state = (r3_state * 2) % (2 ** 23)
    r3_state = r3_state + feedback


def get_majority():
    """Правило большинства. Смотрим на 'оранжевые' ячейки из вашей схемы"""
    c1 = (r1_state // (2 ** 8)) % 2
    c2 = (r2_state // (2 ** 10)) % 2
    c3 = (r3_state // (2 ** 10)) % 2

    if c1 + c2 + c3 >= 2: return 1
    else: return 0


def clock_majority():
    """Сдвигаем только те регистры, которые согласны с большинством"""
    maj = get_majority()

    c1 = (r1_state // (2 ** 8)) % 2
    c2 = (r2_state // (2 ** 10)) % 2
    c3 = (r3_state // (2 ** 10)) % 2

    if c1 == maj: clock_r1()
    if c2 == maj: clock_r2()
    if c3 == maj: clock_r3()


def init_a51(key, frame):
    """Подготовка к шифрованию (заливка ключа и кадра)"""
    global r1_state, r2_state, r3_state
    # Очищаем регистры перед началом нового звонка
    r1_state = 0
    r2_state = 0
    r3_state = 0

    # 1. Загружаем 64 бита ключа
    for i in range(64):
        k_bit = (key // (2 ** i)) % 2
        clock_r1(k_bit)
        clock_r2(k_bit)
        clock_r3(k_bit)

    # 2. Загружаем 22 бита кадра
    for i in range(22):
        f_bit = (frame // (2 ** i)) % 2
        clock_r1(f_bit)
        clock_r2(f_bit)
        clock_r3(f_bit)

    # 3. Разогрев вхолостую (100 тактов)
    for _ in range(100):
        clock_majority()


def get_keystream_bit():
    """Отдаем 1 бит случайного шума"""
    clock_majority()
    out1 = (r1_state // (2 ** 18)) % 2
    out2 = (r2_state // (2 ** 21)) % 2
    out3 = (r3_state // (2 ** 22)) % 2

    return (out1 + out2 + out3) % 2


def encrypt_chunk(data_bytes):
    """Шифруем или расшифровываем кусок звука"""
    res = bytearray()
    for byte in data_bytes:
        gamma_byte = 0
        for i in range(8):
            bit = get_keystream_bit()
            gamma_byte = gamma_byte + (bit * (2 ** (7 - i)))

        res.append(byte ^ gamma_byte)

    return bytes(res)