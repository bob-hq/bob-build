#include <stdio.h>

int main() {
  puts("Hello World!");

#ifdef MESSAGE
  puts(MESSAGE);
#endif

  return 0;
}