#include "system/recf_control_core.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static char reply[160];
static void command(recf_watchdog_t *w,const char *line,uint8_t raw,uint32_t now,const char *expected){
 assert(recf_watchdog_command(w,line,raw,now,true,reply,sizeof reply));
 assert(strstr(reply,expected));
}
int main(void){
 recf_watchdog_t w={0};
 for(unsigned i=0;i<256;i++)assert(recf_watchdog_status(&w,(uint8_t)i,5000)==i);
 command(&w,"@RECF/1 1 123 WATCH_ARM",4,10,"NOT_DISABLED");assert(!w.armed);
 assert(recf_watchdog_command(&w,"@RECF/1 1 123 WATCH_ARM",5,10,false,reply,sizeof reply));assert(strstr(reply,"STARTING"));assert(!w.armed);
 command(&w,"@RECF/1 1 123 WATCH_ARM",5,100,"ARMED");assert(w.armed&&!w.tripped);
 assert(recf_watchdog_status(&w,6,1599)==6);
 assert(recf_watchdog_status(&w,6,1600)==7);assert(w.tripped);
 assert(recf_watchdog_status(&w,0,1601)==1); /* native field disappears: never fall back to driver */
 command(&w,"@RECF/1 2 123 WATCH_BEAT",4,1602,"EXPIRED");assert(w.tripped);
 command(&w,"@RECF/1 3 123 WATCH_ARM",5,1603,"SESSION_EXISTS");assert(w.tripped);
 command(&w,"@RECF/1 1 456 WATCH_ARM",4,1604,"NOT_DISABLED");assert(w.tripped);
 command(&w,"@RECF/1 1 456 WATCH_ARM",5,1700,"ARMED");assert(!w.tripped);
 command(&w,"@RECF/1 2 999 WATCH_BEAT",4,1800,"SESSION");assert(w.last_seen==1700);
 command(&w,"@RECF/1 1 456 WATCH_BEAT",4,1801,"STALE");assert(w.last_seen==1700);
 command(&w,"@RECF/1 2 456 WATCH_BEAT",4,1802,"HEARTBEAT");assert(w.last_seen==1802);
 command(&w,"@RECF/1 3 456 WATCH_STATUS",4,1900,"HEARTBEAT");assert(w.last_seen==1802);
 command(&w,"@RECF/1 3 456 WATCH_STOP",4,1901,"STOPPED");assert(w.tripped);
 assert(recf_watchdog_status(&w,4,1902)==5);
 command(&w,"@RECF/1 1 789 WATCH_ARM",5,UINT32_MAX-500u,"ARMED");
 assert(!(recf_watchdog_status(&w,4,998)&1));
 assert(recf_watchdog_status(&w,4,999)&1);
 recf_core_t software;recf_core_enable(&software,false);assert(w.tripped); /* unrelated state */
 puts("Practice watchdog: default-off, native-field timeout, latched stop, replay, restart, wrap and no fallback passed");
 return 0;
}
