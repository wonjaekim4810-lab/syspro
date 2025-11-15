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

    fp = fopen(argv[1], "wb");
    if (fp == NULL) {
        perror("fopen");
        exit(1);
    }

    printf("%-4s %-15s %-15s %-6s %-10s %-7s\n",
           "ID", "Bookname", "Author", "Year", "BorrowCnt", "Borrow");
    printf("Example → 1 1984 George 1949 7 0\n\n");

    while (scanf("%d %29s %29s %d %d %d",
                 &rec.id, rec.name, rec.author,
                 &rec.year, &rec.borrow_count, &rec.borrowed) == 6) {
        fwrite(&rec, sizeof(rec), 1, fp);
    }

    fclose(fp);
    return 0;
}

