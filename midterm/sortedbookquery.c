#include <stdio.h>
#include <stdlib.h>
#include "student.h"

#define MAX_BOOKS 100

int main(int argc, char *argv[])
{
    struct student arr[MAX_BOOKS];
    int n = 0;
    FILE *fp;
    int mode;
    int i, j;

    if (argc != 2) {
        fprintf(stderr, "How to use: %s FileName\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "rb");
    if (fp == NULL) {
        perror("fopen");
        return 1;
    }

    while (n < MAX_BOOKS && fread(&arr[n], sizeof(struct student), 1, fp) == 1) {
        n++;
    }
    fclose(fp);

    printf("0: list of all books, 1: list of available books ) ");
    scanf("%d", &mode);

    for (i = 0; i < n - 1; i++) {
        for (j = i + 1; j < n; j++) {
            if (arr[i].borrow_count < arr[j].borrow_count) {
                struct student tmp = arr[i];
                arr[i] = arr[j];
                arr[j] = tmp;
            }
        }
    }

    printf("%-4s %-15s %-15s %-6s %-11s %-7s\n",
           "id", "bookname", "author", "year", "numofborrow", "borrow");

    for (i = 0; i < n; i++) {
        if (mode == 1 && arr[i].borrowed != 0)
            continue;

        printf("%-4d %-15s %-15s %-6d %-11d %-7s\n",
               arr[i].id,
               arr[i].name,
               arr[i].author,
               arr[i].year,
               arr[i].borrow_count,
               arr[i].borrowed ? "True" : "False");
    }

    return 0;
}

