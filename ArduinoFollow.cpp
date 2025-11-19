// Arduino Sketch: ROBOT_FOLLOWER_UNCALIBRATED.ino
// Purpose: Controls the robot motors based on serial commands from a Python script.

// ------------------------------------
// 1. Configuration
// ------------------------------------

const long BAUD_RATE = 9600;

// Commands from Python
const char CMD_FORWARD = 'F'; // Move forward (Now the only forward command)
const char CMD_LEFT    = 'L'; // Turn left (center target)
const char CMD_RIGHT   = 'R'; // Turn right (center target)
const char CMD_STOP    = 'S'; // Stop (no target or exit)

// Digital Pins
const int LEFT_PWM_PIN  = 5;   // PWMA - Left Motor Speed (PWM)
const int LEFT_DIR_PIN  = 12;  // BIN1 - Left Motor Direction
const int RIGHT_PWM_PIN = 6;   // PWMB - Right Motor Speed (PWM)
const int RIGHT_DIR_PIN = 7;   // AIN1 - Right Motor Direction
const int STBY_PIN      = 8;   // STBY - Motor Enable Pin

// Base Speeds
const int MOTOR_SPEED = 180; 
const int TURN_SLOW_SPEED = 55; 

// --------------------------------------------------

// ------------------------------------
// 2. Setup
// ------------------------------------

void setup() {
  Serial.begin(BAUD_RATE);
  
  // Set motor control pins as outputs
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);
  pinMode(STBY_PIN, OUTPUT);
  
  // Enable the motor driver
  digitalWrite(STBY_PIN, HIGH);
  
  Serial.println("Arduino Follower Sketch Ready. Using Uncalibrated Speed.");
  
  // Safety: Ensure motors are stopped at program start
  stopMotors(); 
}

// ------------------------------------
// 3. Motor Control Functions
// ------------------------------------

// Stop both motors
void stopMotors() {
  digitalWrite(LEFT_DIR_PIN, LOW);
  digitalWrite(RIGHT_DIR_PIN, LOW);
  analogWrite(LEFT_PWM_PIN, 0);  
  analogWrite(RIGHT_PWM_PIN, 0);  
  Serial.println("ACTION: STOP");
}

// Drive both motors forward
void moveForward() {
  // Set Direction for Forward (LOW)
  digitalWrite(LEFT_DIR_PIN, LOW); 
  digitalWrite(RIGHT_DIR_PIN, LOW);
  
  // Apply Equal Speeds
  analogWrite(LEFT_PWM_PIN, MOTOR_SPEED);
  analogWrite(RIGHT_PWM_PIN, MOTOR_SPEED);
  
  Serial.print("ACTION: FORWARD. L:");
  Serial.print(MOTOR_SPEED);
  Serial.print(", R:");
  Serial.println(MOTOR_SPEED);
}

// Turn left (Left slows, Right maintains speed)
void turnLeft() {
  digitalWrite(LEFT_DIR_PIN, LOW);
  digitalWrite(RIGHT_DIR_PIN, LOW);
  analogWrite(LEFT_PWM_PIN, TURN_SLOW_SPEED);
  analogWrite(RIGHT_PWM_PIN, MOTOR_SPEED); 
  Serial.println("ACTION: LEFT (Smooth)");
}

// Turn right (Right slows, Left maintains speed)
void turnRight() {
  digitalWrite(LEFT_DIR_PIN, LOW);
  digitalWrite(RIGHT_DIR_PIN, LOW);
  analogWrite(LEFT_PWM_PIN, MOTOR_SPEED);
  analogWrite(RIGHT_PWM_PIN, TURN_SLOW_SPEED);
  Serial.println("ACTION: RIGHT (Smooth)");
}


// ------------------------------------
// 4. Main Loop
// ------------------------------------

void loop() {
  // Check if any data has been sent from the Python script
  if (Serial.available() > 0) {
    char command = Serial.read();  

    // Process the command
    switch (command) {
      case CMD_FORWARD:
        moveForward();
        break;
      case CMD_LEFT:
        turnLeft();
        break;
      case CMD_RIGHT:
        turnRight();
        break;
      case CMD_STOP:
        stopMotors();
        break;
      default:
        Serial.print("Ignoring unknown command: ");
        Serial.println(command);
        break;
    }
  }
}