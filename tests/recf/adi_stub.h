#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "pros/adi.h"
#define E_DEVICE_MOTOR 2
#define E_DEVICE_ADI 12
#define ADI_MOTOR_MAX_SPEED 127
#define ADI_MOTOR_MIN_SPEED -128
typedef struct {int config[8],value[8];} info_t;
typedef struct {int device_type;info_t *device_info;} v5_smart_device_s_t;
static info_t banks[22];
static v5_smart_device_s_t devices[22];
typedef info_t *V5_DeviceT;
typedef int V5_AdiPortConfiguration;
static bool blocked;
static int config_writes,value_writes,motor_writes,led_writes;
#define claim_port_i(port,type) v5_smart_device_s_t *device=&devices[(port)]; (void)(type)
#define return_port(port,value) return (value)
static bool recf_control_output_blocked(void){return blocked;}
static void vexDeviceAdiPortConfigSet(info_t *d,unsigned p,int v){d->config[p]=v;config_writes++;}
static int vexDeviceAdiPortConfigGet(info_t *d,unsigned p){return d->config[p];}
static void vexDeviceAdiValueSet(info_t *d,unsigned p,int v){d->value[p]=v;value_writes++;}
static void vexDeviceMotorVoltageSet(info_t *d,int v){(void)d;assert(v==0);motor_writes++;}
static void port_mutex_take_all(void){}
static void port_mutex_give_all(void){}
static void rtos_suspend_all(void){}
static void rtos_resume_all(void){}
static v5_smart_device_s_t *registry_get_device_internal(unsigned p){assert(p<22);return &devices[p];}

static int32_t vexDeviceAdiAddrLedSet(info_t *d,uint32_t p,uint32_t *data,uint32_t offset,uint32_t length,uint32_t options){(void)d;(void)p;(void)data;(void)offset;(void)length;(void)options;led_writes++;return 1;}
