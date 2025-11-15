CC = gcc
CFLAGS = -Wall -Wextra -lm -fsanitize=address

SRC = utils.c path.c
OBJ = ${SRC:.c=.o}
DEP = ${SRC:.c=.d}

all: path

path: ${OBJ}
	${CC} -o $@ $^ ${CFLAGS}



-include ${DEP}

.PHONY: clean

clean:
	${RM} ${OBJ}
	${RM} ${DEP}
	${RM} utils.o
	${RM} path.o