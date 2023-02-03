// inputs : 4~11
// outputs : 22~25

// pin range
int first_in = 4;
int last_in = 5;
int first_out = 22;
int last_out = 25;

const int n_out = 4;


int pin_dict_in[] = {4,5,6,7,8,9,10,11};
int pin_dict_out[n_out] = {22,23,24,25};

const int BUFFER_SIZE = 4;
// 0x0A/0x0B, number output/input, state, valid
byte recv_data[BUFFER_SIZE];
byte send_data[BUFFER_SIZE] = {0xC0, 0x00, 0x00, 0x00}; // x, number input, x, valid
byte temp[BUFFER_SIZE] = {0xFF, 0x00, 0x00, 0xFF};

int light_time[n_out] = {0,0,0,0};

int rlen;

void setup() {
  Serial.begin(9600);

  // output
  for(int i=first_out;i<=last_out;i++) pinMode(i, OUTPUT);

  // input
  for(int i=first_in;i<=last_in;i++) pinMode(i, INPUT);

  // init
  for(int i=first_out;i<=last_out;i++) digitalWrite(i, LOW);
  for(int i=first_in;i<=last_in;i++) digitalRead(i);
}

void loop() {
  if(Serial.available()){
    rlen = Serial.readBytes(recv_data, BUFFER_SIZE);
    // if(rlen) Serial.write(recv_data, 4);/

    // validation
    bool valid_check = true;
    if(rlen != 4) valid_check = false;
    if((recv_data[0]^recv_data[1]^recv_data[2]) != recv_data[3]) valid_check = false;
    if(!valid_check) Serial.write(temp, BUFFER_SIZE);

    // request turn on/off
    if(valid_check && recv_data[0] == 0xA0){ // ex) 0xA0 0x02 0x01 0xA3 -> pin 24 turn on
      int idx = recv_data[1];
      bool state = recv_data[2];
      light_time[idx] = 1;
      digitalWrite(pin_dict_out[idx], state);
    }

    // request sensor value
    if(valid_check && recv_data[0] == 0xB0){ // ex) 0xB0 0x01 0x00 0xB1 -> what value pin 5
      int idx = recv_data[1];
      bool value = digitalRead(pin_dict_in[idx]);

      send_data[1] = idx;
      send_data[2] = value;
      send_data[3] = send_data[0] ^ send_data[1] ^ send_data[2];
      Serial.write(send_data, BUFFER_SIZE);
    }
  }

  // prevention overheating
  for(int i=0;i<n_out;i++){
    if(!light_time[i]) continue;
    if(100 < light_time[i]){
      light_time[i] = 0;
      digitalWrite(pin_dict_out[i], LOW);
    }
    else light_time[i] += 1;
  }


  delay(5);
}
