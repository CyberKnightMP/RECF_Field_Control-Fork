#include "system/recf_control_core.h"
#include <stdio.h>
#include <string.h>
int main(void) {
    recf_core_t s;recf_core_enable(&s,true);
    char line[256],reply[128],command[128];unsigned long now;unsigned raw;
    while(fgets(line,sizeof(line),stdin)) {
        if(sscanf(line,"%lu %u %127[^\n]",&now,&raw,command)!=3)return 2;
        recf_core_command(&s,command,(uint8_t)raw,(uint32_t)now,reply,sizeof(reply));
        fputs(reply,stdout);
    }
}
