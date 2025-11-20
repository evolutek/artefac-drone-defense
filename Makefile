CC = gcc
DB-CFLAGS = -Wall -Wextra -fsanitize=address
CFLAGS = -lm

SRC_ALGO = src/algo/utils.c src/algo/pretraitement.c
OBJ = ${SRC:.c=.o}

all: algo

algo:
	${CC} ${SRC_ALGO} -o build/$@ ${CFLAGS} ${DB-CFLAGS}

.PHONY: clean

clean:
	${RM} build/*
