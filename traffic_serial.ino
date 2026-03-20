int GREEN = 8;
int RED   = 9;

void setup()
{
  pinMode(GREEN, OUTPUT);
  pinMode(RED, OUTPUT);

  Serial.begin(9600);
}

void loop()
{
  if (Serial.available() > 0)
  {
    char data = Serial.read();

    if (data == 'G')     // GREEN signal
    {
      digitalWrite(GREEN, HIGH);
      digitalWrite(RED, LOW);
    }

    else if (data == 'R')   // RED signal
    {
      digitalWrite(GREEN, LOW);
      digitalWrite(RED, HIGH);
    }
  }
}