#include <DHT.h>
#include <dimmable_light.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>
#include <WiFi.h>
#include "time.h"
#include <SPIFFS.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>


#define DHTPIN 4
#define DHTTYPE DHT11
#define LIGHT_PIN 12
#define Z_C_PIN 5

DHT dht(DHTPIN, DHTTYPE);
DimmableLight light(LIGHT_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

unsigned long intervaloVerificacao = 60000 * 10;  // A cada 60 segundos (1 minuto)
unsigned long ultimoTempoVerificacao = 0;

const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -3 * 3600;  // GMT-3 (ajuste se necessário)
const int daylightOffset_sec = 0;

const char* servidorAPI = "https://aquecerto.onrender.com/esp32";

const char *code = "/codigo.txt";
const char *config = "/config.txt";

unsigned long tempoUltimaTela = 0;
const unsigned long intervaloTela = 5000;  // 5 segundos
int estadoDisplay = 0;  // 0: temp e luz, 1: min/max, 2: código

String ultimaData = "";


String codigo;
float tempMax;
float tempMin;
int dia;

// ======= Wi-Fi ==========
const char* ssid = "iPhone de Gabriel";
const char* password = "senha123";

// Função para gerar código aleatório de 6 caracteres alfanuméricos
String gerarCodigo() {
  const char caracteres[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  String codigo = "";
  for (int i = 0; i < 6; i++) {
    int index = random(0, strlen(caracteres));
    codigo += caracteres[index];
  }
  return codigo;
}

int calcularBrilho(float tempMin, float tempMax, float temperaturaAtual) {
  float tempMeio = (tempMin + tempMax) / 2.0;
  int brilho = 0;

  if (temperaturaAtual <= tempMin) {
    brilho = 255;
  } else if (temperaturaAtual > tempMin && temperaturaAtual <= tempMeio) {
    brilho = map(temperaturaAtual * 100, tempMin * 100, tempMeio * 100, 255, 0);
    brilho = constrain(brilho, 0, 255);
  } else {
    brilho = 0;
  }

  return brilho;
}

void atualizarLCD(float temperatura, int brilho) {
  int percent = map(brilho, 0, 255, 0, 100);

  lcd.clear();

  if (estadoDisplay == 0) {
    // Exibe temperatura atual e luz
    lcd.setCursor(0, 0);
    lcd.print("Temp: ");
    lcd.print(temperatura, 1);
    lcd.print(" C");

    lcd.setCursor(0, 1);
    lcd.print("Luz: ");
    lcd.print(percent);
    lcd.print(" %");

  } else if (estadoDisplay == 1) {
    // Exibe temp min e max
    lcd.setCursor(0, 0);
    lcd.print("Min: ");
    lcd.print(tempMin, 1);
    lcd.print(" C");

    lcd.setCursor(0, 1);
    lcd.print("Max: ");
    lcd.print(tempMax, 1);
    lcd.print(" C");

  } else if (estadoDisplay == 2) {
    // Exibe código
    lcd.setCursor(0, 0);
    lcd.print("Codigo:");

    lcd.setCursor(0, 1);
    lcd.print(codigo);
  }

  // Atualiza para próxima tela no próximo ciclo
  estadoDisplay = (estadoDisplay + 1) % 3;
}

String carregarCodigo(const char *arquivo) {
  if (SPIFFS.exists(arquivo)) {
    File file = SPIFFS.open(arquivo, "r");
    if (file) {
      String codigo = file.readString();
      codigo.trim();
      file.close();
      Serial.println("Arquivo existente encontrado.");
      Serial.print("Código: ");
      Serial.println(codigo);
      return codigo;
    } else {
      Serial.println("Erro ao abrir o arquivo existente.");
      return "";
    }
  } else {
    String codigo = gerarCodigo();
    File file = SPIFFS.open(arquivo, "w");
    if (file) {
      file.print(codigo);
      file.close();
      Serial.println("Arquivo criado com sucesso.");
      Serial.print("Novo Código: ");
      Serial.println(codigo);
      return codigo;
    } else {
      Serial.println("Erro ao criar o arquivo.");
      return "";
    }
  }
}

void carregarConfig(const char* arquivo) {
  if (SPIFFS.exists(arquivo)) {
    File file = SPIFFS.open(arquivo, "r");
    if (file) {
      StaticJsonDocument<512> doc;
      DeserializationError erro = deserializeJson(doc, file);

      if (!erro) {
        tempMin = doc["min"] | 31.0;
        tempMax = doc["max"] | 33.0;
        dia = doc["dia"] | 0;
        ultimaData = doc["ultimaData"] | obterDataAtual();

        Serial.printf("Config -> Min: %.1f, Max: %.1f, dia: %d, Data: %s\n", tempMin, tempMax, dia, ultimaData.c_str());
      } else {
        Serial.println("Erro ao ler config, usando padrão.");
        tempMin = 31.0;
        tempMax = 33.0;
        dia = 0;
        ultimaData = obterDataAtual();
      }
      file.close();
    }
  } else {
    // Se não existir, cria com padrão
    tempMin = 31.0;
    tempMax = 33.0;
    dia = 0;
    ultimaData = obterDataAtual();
    salvarConfig(arquivo);
  }
}


void enviarDadosAPI(float temperatura, int brilho) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("https://aquecerto.onrender.com/esp32");  // Corrigido o endereço
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<256> json;
    json["code"] = codigo;
    json["temperature"] = temperatura;
    json["brightness"] = map(brilho, 0, 255, 0, 100);
    json["min"] = tempMin;
    json["max"] = tempMax;

    String jsonString;
    serializeJson(json, jsonString);

    int httpResponseCode = http.POST(jsonString);

    if (httpResponseCode > 0) {
      Serial.print("Resposta da API: ");
      Serial.println(httpResponseCode);
      String payload = http.getString();
      Serial.println(payload);
    } else {
      Serial.print("Erro na requisição: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi desconectado.");
  }
}


void salvarConfig(const char* arquivo) {
  StaticJsonDocument<512> doc;
  doc["min"] = tempMin;
  doc["max"] = tempMax;
  doc["dia"] = dia;
  doc["ultimaData"] = ultimaData;

  File file = SPIFFS.open(arquivo, "w");
  if (file) {
    serializeJson(doc, file);
    file.close();
    Serial.println("Configuração salva.");
  } else {
    Serial.println("Erro ao salvar configuração.");
  }
}

void iniciarWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Conectado!");

  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
}

String obterDataAtual() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Falha ao obter hora NTP");
    return "";
  }

  char data[11];
  strftime(data, sizeof(data), "%Y-%m-%d", &timeinfo);
  return String(data);
}

void verificarMudancaDeDia() {
  String dataAtual = obterDataAtual();

  if (dataAtual != "" && dataAtual != ultimaData) {
    dia++;
    ultimaData = dataAtual;
    Serial.println("Novo dia detectado!");
    Serial.printf("dia atualizados: %d\n", dia);

    salvarConfig(config);
  }
}

void setup() {
  Serial.begin(115200);
  lcd.init();
  dht.begin();
  DimmableLight::setSyncPin(Z_C_PIN);
  DimmableLight::begin();
  
  lcd.backlight();

  // Inicializa o SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("Erro ao montar SPIFFS");
    return;
  }
  
  iniciarWiFi();

  codigo = carregarCodigo(code);
  carregarConfig(config);
}

void loop() {
  unsigned long tempoAtual = millis();

  if (tempoAtual - ultimoTempoVerificacao >= intervaloVerificacao) {
    ultimoTempoVerificacao = tempoAtual;
    verificarMudancaDeDia();
  }







  float temperature = dht.readTemperature();
  int brightness = 0;

  if (!isnan(temperature)) {
    brightness = calcularBrilho(tempMin, tempMax, temperature);
    light.setBrightness(brightness);
    enviarDadosAPI(temperature, brightness);

    if (millis() - tempoUltimaTela >= intervaloTela) {
      tempoUltimaTela = millis();
      atualizarLCD(temperature, brightness);
    }

} else {
  Serial.println("Erro ao ler o sensor!");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Sensor erro!");
}

  delay(2000);
}
