CC = gcc
CPPFLAGS := -I src
CFLAGS := -Wall -Wextra -Werror -O0 -g -march=native #-fsanitize=address 
LDFLAGS := -lm -lpthread 

SRC = $(wildcard src/**/*.c) src/main.c
OBJ = $(SRC:.c=.o)

TARGET := build/algo

.PHONY: clean all

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	$(RM) $(TARGET)
	$(RM) $(OBJ)
