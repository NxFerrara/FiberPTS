#pragma once
#include <stddef.h>
#include <stdint.h>

char *get_machine_id();
void send_data_to_pipe(const char *data);
void get_current_time_in_est(char *buffer, const char *format);
void uint_to_hexstr(const uint8_t *uid, size_t uid_len, char *uid_str);
int is_debounce_time_passed(struct timespec current_time, struct timespec last_release, int debounce_time);