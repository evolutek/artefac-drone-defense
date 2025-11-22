CC = gcc
DB-CFLAGS = -Wall -Wextra -fsanitize=address -g
CFLAGS = -lm

SRC_ALGO = utils.c pretraitement.c
OBJ = ${SRC:.c=.o}

all: algo

algo:
	${CC} ${SRC_ALGO} -o $@ ${CFLAGS} ${DB-CFLAGS}

.PHONY: clean

clean:
	${RM} build/*
