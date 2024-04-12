from ctypes import CDLL, c_char_p, c_size_t, create_string_buffer

lib = CDLL("./poll.so")
lib.poll.argtypes = [c_char_p, c_size_t]

uid_len = 64

while True:
    uid_str = create_string_buffer(uid_len)
    lib.poll(uid_str, uid_len)
    print("UID String:", uid_str.value.decode('utf-8'))

