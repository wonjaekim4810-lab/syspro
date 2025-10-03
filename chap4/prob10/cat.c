#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    FILE *fp;
    int c;
    int line_number = 1;
    int with_line_numbers = 0;
    int start_index = 1;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s [-n] file1 [file2 ...]\n", argv[0]);
        exit(1);
    }
    if (strcmp(argv[1], "-n") == 0) {
        with_line_numbers = 1;
        start_index = 2;
    }
    for (int i = start_index; i < argc; i++) {
        fp = fopen(argv[i], "r");
        if (fp == NULL) {
            perror(argv[i]);
            continue;
        }

        if (with_line_numbers) {
            printf("%6d  ", line_number++);
        }

        while ((c = getc(fp)) != EOF) {
            putchar(c);

            if (with_line_numbers && c == '\n') {
                printf("%6d  ", line_number++);
            }
        }

        fclose(fp);
    }

    return 0;
}

