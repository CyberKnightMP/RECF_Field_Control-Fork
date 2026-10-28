int main(void){
 for(int i=0;i<22;i++){devices[i].device_info=&banks[i];devices[i].device_type=E_DEVICE_ADI;}
 devices[1].device_type=E_DEVICE_MOTOR;
 for(int port=1;port<=22;port+=21){
  info_t *b=&banks[port-1]; blocked=false;
  assert(ext_adi_port_set_config(port,'A',E_ADI_DIGITAL_OUT)==1);
  assert(ext_adi_digital_write(port,'A',true)==1 && b->value[0]==1);
  b->config[1]=E_ADI_LEGACY_PWM;b->config[2]=E_ADI_LEGACY_SERVO;
  assert(ext_adi_motor_set(port,'B',100)==1 && b->value[1]==100);
  assert(ext_adi_motor_set(port,'C',80)==1 && b->value[2]==80);
  blocked=true;int old=config_writes;
  assert(recf_adi_led_set(b,0,NULL,0,0,0)==PROS_ERR && led_writes==0);
  assert(ext_adi_port_set_config(port,'A',E_ADI_ANALOG_OUT)==PROS_ERR && errno==EACCES);
  assert(config_writes==old && b->config[0]==E_ADI_DIGITAL_OUT);
  assert(ext_adi_digital_write(port,'A',false)==PROS_ERR && b->value[0]==1);
  assert(ext_adi_port_set_value(port,'A',0)==PROS_ERR && b->value[0]==1);
  assert(ext_adi_motor_set(port,'B',127)==1 && b->value[1]==0);
  assert(ext_adi_motor_set(port,'C',0)==PROS_ERR && b->value[2]==80);
  b->value[1]=100;recf_control_stop_motors();
  assert(b->value[1]==0 && b->value[0]==1 && b->value[2]==80);
  blocked=false;assert(ext_adi_digital_write(port,'A',false)==1 && b->value[0]==0);
 }
 assert(motor_writes==2);puts("ADI: internal/expander valve and servo hold, PWM neutral, config/write blocking and resume passed");return 0;
}
