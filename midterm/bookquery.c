#include <stdio.h>
#include <stdlib.h>
#include "student.h"

int main(int argc, char* argv[]) {
    struct student rec;
    FILE *fp;

    if (argc != 2) {
        fprintf(stderr, "How to use: %s FileName\n", argv[0]);
        exit(1);
    }

    fp = fopen(argv[1], "rb");
    if (fp == NULL) {
        perror("fopen");
        exit(1);
    }

    printf("%-4s %-15s %-15s %-6s %-10s %-7s\n",
           "ID", "Bookname", "Author", "Year", "BorrowCnt", "Borrow");

    while (fread(&rec, sizeof(rec), 1, fp) == 1) {
        printf("%-4d %-15s %-15s %-6d %-10d %-7s\n",
               rec.id, rec.name, rec.author, rec.year,
               rec.borrow_count, rec.borrowed ? "True" : "False");
    }

    fclose(fp);
    return 0;
}

