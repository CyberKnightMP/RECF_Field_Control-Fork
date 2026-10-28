int main(void){
 blocked=true;
 assert(motor_move(1,127)==1);
 assert(motor_move_voltage(-1,12000)==1);
 assert(motor_move_velocity(1,200)==1);
 assert(motor_move_absolute(1,360,200)==1);
 assert(motor_move_relative(1,360,200)==1);
 assert(motor_modify_profiled_velocity(1,200)==1);
 assert(motor_brake(1)==1);
 assert(voltage_calls==7 && velocity_calls==0 && target_calls==0 && last_value==0);
 blocked=false;
 assert(motor_move_voltage(-1,4000)==1 && last_value==-4000);
 assert(motor_move_velocity(-1,100)==1 && last_value==-100);
 assert(motor_move_absolute(1,360,150)==1 && target_calls==1 && last_value==150);
 assert(motor_move_relative(1,360,150)==1 && target_calls==2);
 assert(motor_modify_profiled_velocity(1,100)==1 && velocity_calls==2);
 assert(motor_move(1,127)==1 && last_value==12000);
 return 0;
}
