#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#define E_DEVICE_MOTOR 1
#define PROS_SUCCESS 1
static bool blocked;
static int voltage_calls,target_calls,velocity_calls,last_value;
static struct {void *device_info;} fake_device;
#define claim_port_i(port,type) (void)(port); (void)(type); __typeof__(fake_device) *device = &fake_device
#define return_port(port,value) return (value)
static bool recf_control_output_blocked(void){return blocked;}
static void vexDeviceMotorVoltageSet(void *d,int v){(void)d;voltage_calls++;last_value=v;}
static void vexDeviceMotorVelocitySet(void *d,int v){(void)d;velocity_calls++;last_value=v;}
static void vexDeviceMotorVelocityUpdate(void *d,int v){(void)d;velocity_calls++;last_value=v;}
static void vexDeviceMotorAbsoluteTargetSet(void *d,double p,int v){(void)d;(void)p;target_calls++;last_value=v;}
static void vexDeviceMotorRelativeTargetSet(void *d,double p,int v){(void)d;(void)p;target_calls++;last_value=v;}
int32_t motor_move_voltage(int8_t port,int32_t voltage);
int32_t motor_move_velocity(int8_t port,int32_t velocity);
