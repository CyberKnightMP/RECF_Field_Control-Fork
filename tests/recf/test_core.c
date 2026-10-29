#include "system/recf_control_core.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static recf_core_t s;
static char reply[128];
static void cmd(const char *line,uint8_t raw,uint32_t time,const char *expect) {
    assert(recf_core_command(&s,line,raw,time,reply,sizeof(reply))>0);
    if(!strstr(reply,expect)){fprintf(stderr,"Expected %s in %s",expect,reply);assert(0);}
}
static char ordinary[1024],frames[1024];static size_t no,nf;
static void out(const char *p,size_t n,void *u){(void)u;memcpy(ordinary+no,p,n);no+=n;}
static void frame(const char *p,size_t n,void *u){(void)u;memcpy(frames+nf,p,n);nf+=n;}
int main(void) {
    recf_core_enable(&s,false);
    for(unsigned raw=0;raw<16;++raw)assert(recf_core_status(&s,raw,0)==raw);
    cmd("@RECF/1 1 20 HELLO",0,0,"ERR DRIVER PHYSICAL 0 LOCKED");
    recf_core_enable(&s,true);
    s.ready=false;cmd("@RECF/1 1 20 HELLO",0,99,"STARTING");s.ready=true;
    cmd("@RECF/1 1 20 HELLO",0,100,"OK STOP SOFTWARE 0 CLAIMED");
    cmd("@RECF/1 1 20 AUTON",0,110,"ERR STOP SOFTWARE 0 STALE");
    cmd("@RECF/1 2 20 AUTON",0,120,"OK AUTON SOFTWARE");
    assert(recf_core_status(&s,0,130)==2);
    cmd("@RECF/1 3 21 DRIVER",0,140,"SESSION");
    cmd("@RECF/1 4 21 HELLO",0,150,"BUSY");
    cmd("@RECF/1 4 20 HELLO",0,160,"SESSION_EXISTS");
    cmd("@RECF/1 3 20 BOGUS",0,170,"COMMAND");
    assert(s.sequence==2 && s.last_seen==120);
    cmd("@RECF/1 3 20 PING",0,500,"OK AUTON SOFTWARE");
    cmd("@RECF/1 4 20 STATUS",0,1999,"OK AUTON SOFTWARE");
    assert(recf_core_status(&s,0,2000)==1); assert(s.session==0);
    cmd("@RECF/1 5 20 DRIVER",0,2001,"SESSION");
    cmd("@RECF/1 6 21 HELLO",0,2002,"OK STOP SOFTWARE");
    cmd("@RECF/1 7 21 DRIVER",0,2003,"OK DRIVER SOFTWARE");
    assert(recf_core_status(&s,13,2004)==13); assert(s.session==0);
    assert(recf_core_status(&s,14,2005)==14); // Field auton cannot be changed by software.
    cmd("@RECF/1 8 21 STOP",14,2006,"ERR AUTON FIELD 14 FIELD");
    assert(recf_core_status(&s,0,2007)==1); // Disconnect does not resurrect driver mode.
    cmd("@RECF/1 9 22 HELLO",0,2008,"OK STOP SOFTWARE");
    cmd("@RECF/1 10 22 AUTON",0,2009,"OK AUTON SOFTWARE");
    assert(recf_core_status(&s,1,2010)==1); // Physical disable without connected is respected.
    cmd("@RECF/1 11 22 DRIVER",1,2011,"FIELD");
    cmd("@RECF/1 11 22 STOP",0,2012,"OK STOP SOFTWARE");
    cmd("@RECF/1 12 22 RELEASE",0,2013,"OK DRIVER PHYSICAL");
    assert(!s.selected);
    cmd("@RECF/1 13 22 AUTON",0,2014,"SESSION");
    recf_core_enable(&s,true);
    cmd("@RECF/1 1 23 HELLO",0,UINT32_MAX-1000,"OK STOP SOFTWARE");
    cmd("@RECF/1 2 23 AUTON",0,UINT32_MAX-900,"OK AUTON SOFTWARE");
    assert(recf_core_status(&s,0,598)==2);
    assert(recf_core_status(&s,0,599)==1); // uint32 millisecond rollover.
    const char *bad[]={"", "@RECF/2 1 1 HELLO", "@RECF/1 0 1 HELLO", "@RECF/1 -1 1 HELLO", "@RECF/1 4294967296 1 HELLO", "@RECF/1 1 4294967296 HELLO", "@RECF/1 1 1", "@RECF/1 1 1 AUTON extra"};
    for(size_t i=0;i<sizeof(bad)/sizeof(*bad);++i)cmd(bad[i],0,1000,"ERR");
    recf_parser_t p={0};
    const char *input="abc@x\n@RECF/1 1 2 HELLO\nxyz\n";
    for(size_t i=0;i<strlen(input);++i)recf_parser_feed(&p,input[i],i,out,frame,NULL);
    assert(!memcmp(ordinary,"abc@x\nxyz\n",no));assert(no==10);
    assert(nf==strlen("@RECF/1 1 2 HELLO"));
    assert(!memcmp(frames,"@RECF/1 1 2 HELLO",nf));
    // Overlong and binary frames are dropped, not forwarded into application stdin.
    no=nf=0;memset(&p,0,sizeof(p));
    input="@RECF/1 ";for(size_t i=0;i<strlen(input);++i)recf_parser_feed(&p,input[i],0,out,frame,NULL);
    for(int i=0;i<200;++i)recf_parser_feed(&p,'X',0,out,frame,NULL);
    recf_parser_feed(&p,'\n',0,out,frame,NULL);assert(!no&&!nf);
    // Expired partial reserved frames cannot execute when the remainder arrives.
    for(size_t i=0;i<strlen(input);++i)recf_parser_feed(&p,input[i],0,out,frame,NULL);
    recf_parser_feed(&p,'x',500,out,frame,NULL);assert(no==1&&ordinary[0]=='x');
    recf_core_t brains[4]={0}; char brain_reply[4][128];
    for(size_t i=0;i<4;++i){
        char hello[40];
        recf_core_enable(&brains[i],true);
        snprintf(hello,sizeof(hello),"@RECF/1 1 %u HELLO",(unsigned)(100+i));
        assert(recf_core_command(&brains[i],hello,0,10,brain_reply[i],sizeof(brain_reply[i]))>0);
        assert(strstr(brain_reply[i],"OK STOP SOFTWARE"));
    }
    assert(recf_core_command(&brains[2],"@RECF/1 2 102 AUTON",0,20,
                             brain_reply[2],sizeof(brain_reply[2]))>0);
    for(size_t i=0;i<4;++i)
        assert(recf_core_status(&brains[i],0,30)==(i==2 ? RECF_AUTONOMOUS : RECF_DISABLED));
    assert(!strcmp(recf_mode_name((recf_mode_t)-1),"UNKNOWN"));
    assert(!strcmp(recf_mode_name((recf_mode_t)4),"UNKNOWN"));
    puts("RECF core: arbitration, leases, rollover, sessions, parser, malformed-frame and four-instance tests passed");
}
