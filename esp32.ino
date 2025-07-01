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

unsigned long intervaloVerificacao = 60000 * 10;  // A cada 10 minutos
unsigned long ultimoTempoVerificacao = 0;

const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -3 * 3600;
const int daylightOffset_sec = 0;

// ==================== NOVO: Constantes do Supabase ====================
// ATENÇÃO: Substitua pelos dados do seu projeto Supabase
const char* supabaseUrl = "https://rktybanymktqkjyopcrd.supabase.co/rest/v1/campanulas";
const char* supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJrdHliYW55bWt0cWtqeW9wY3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzNzIxMjcsImV4cCI6MjA2Njk0ODEyN30.8bUcaM1MdjcuWoMsbqaDFoBM4YDY8p5nXfkMRNgjEz0";
// =====================================================================

const char *code = "/codigo.txt";
const char *config = "/config.txt";

unsigned long tempoUltimaTela = 0;
const unsigned long intervaloTela = 5000;  // 5 segundos
int estadoDisplay = 0;

String ultimaData = "";
String codigo;
float tempMax;
float tempMin;
int dia;

// Wi-Fi
const char* ssid = "PROJETO";
const char* password = "projeto123";

// ==================== Funções ====================

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
    lcd.setCursor(0, 0);
    lcd.print("Temp: ");
    lcd.print(temperatura, 1);
    lcd.print(" C");

    lcd.setCursor(0, 1);
    lcd.print("Luz: ");
    lcd.print(percent);
    lcd.print(" %");

  } else if (estadoDisplay == 1) {
    lcd.setCursor(0, 0);
    lcd.print("Min: ");
    lcd.print(tempMin, 1);
    lcd.print(" C");

    lcd.setCursor(0, 1);
    lcd.print("Max: ");
    lcd.print(tempMax, 1);
    lcd.print(" C");

  } else if (estadoDisplay == 2) {
    lcd.setCursor(0, 0);
    lcd.print("Codigo: ");

    lcd.setCursor(0, 1);
    lcd.print(codigo);
  }

  estadoDisplay = (estadoDisplay + 1) % 3;
}

String carregarCodigo(const char *arquivo) {
  if (SPIFFS.exists(arquivo)) {
    File file = SPIFFS.open(arquivo, "r");
    if (file) {
      String codigo = file.readString();
      codigo.trim();
      file.close();
      return codigo;
    }
  }

  String codigo = gerarCodigo();
  File file = SPIFFS.open(arquivo, "w");
  if (file) {
    file.print(codigo);
    file.close();
  }
  return codigo;
}

String obterDataAtual() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return "";
  char data[11];
  strftime(data, sizeof(data), "%Y-%m-%d", &timeinfo);
  return String(data);
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
      } else {
        tempMin = 31.0;
        tempMax = 33.0;
        dia = 0;
        ultimaData = obterDataAtual();
      }
      file.close();
    }
  } else {
    tempMin = 31.0;
    tempMax = 33.0;
    dia = 0;
    ultimaData = obterDataAtual();
    salvarConfig(arquivo);
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
  }
}

// ==================== MODIFICADO: Função para INSERIR ou ATUALIZAR dados no Supabase ====================
void enviarDadosSupabase(float temperatura, int brilho) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(supabaseUrl);

    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", supabaseKey);
    http.addHeader("Authorization", "Bearer " + String(supabaseKey));
    http.addHeader("Prefer", "resolution=merge-duplicates");

    StaticJsonDocument<256> doc;
    JsonArray data = doc.to<JsonArray>();
    JsonObject item = data.createNestedObject();
    Serial.println(dia);
    item["id"] = codigo;
    item["temp_atual"] = temperatura;
    item["intensidade"] = map(brilho, 0, 255, 0, 100);
    item["dia"] = dia;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    Serial.println("Enviando para o Supabase: " + jsonPayload);

    int httpCode = http.POST(jsonPayload);

    if (httpCode > 0) {
      Serial.printf("[Supabase] Código de resposta: %d\n", httpCode);
      if (httpCode != 200 && httpCode != 201) {
        String response = http.getString();
        Serial.println("[Supabase] Resposta: " + response);
      } else {
        Serial.println("[Supabase] Dados atualizados com sucesso!");
      }
    } else {
      Serial.printf("[Supabase] Falha na requisição: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();
  } else {
    Serial.println("WiFi não conectado. Não foi possível enviar para o Supabase.");
  }
}

// ========================================================================================================

void iniciarWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Conectado!");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
}

void verificarMudancaDeDia() {
  String dataAtual = obterDataAtual();
  Serial.print("verificando");
  Serial.print(dataAtual);
  Serial.print(ultimaData);
  if (dataAtual != "" && dataAtual != ultimaData) {
    dia += 1;
    ultimaData = dataAtual;
    salvarConfig(config);
    Serial.print("atualizado");
  }
}

void obterConfigDoSupabase() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String url = String(supabaseUrl) + "?id=eq." + codigo + "&select=temp_min,temp_max,dia";
    http.begin(url);

    http.addHeader("apikey", supabaseKey);
    http.addHeader("Authorization", "Bearer " + String(supabaseKey));

    int httpCode = http.GET();
    if (httpCode == 200) {
      String payload = http.getString();
      StaticJsonDocument<512> doc;
      DeserializationError erro = deserializeJson(doc, payload);

      if (!erro && doc.is<JsonArray>() && !doc.as<JsonArray>().isNull() && doc.as<JsonArray>().size() > 0) {
        JsonObject obj = doc[0];
        if (obj.containsKey("temp_min")) tempMin = obj["temp_min"].as<float>();
        if (obj.containsKey("temp_max")) tempMax = obj["temp_max"].as<float>();
        if (obj.containsKey("dia"))     dia     = obj["dia"].as<int>();
        salvarConfig(config);  // salva localmente
        Serial.println("[Supabase] Configuração carregada com sucesso");
      } else {
        Serial.println("[Supabase] Erro ao interpretar JSON ou resposta vazia");
      }
    } else {
      Serial.printf("[Supabase] Erro na requisição: %d\n", httpCode);
    }

    http.end();
  } else {
    Serial.println("[Supabase] WiFi não conectado!");
  }
}


// ==================== Setup & Loop ====================

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  dht.begin();

  DimmableLight::setSyncPin(Z_C_PIN);
  DimmableLight::begin();

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
  
  ultimaData = "2025-01-01"; // Forçar diferença para simular
  verificarMudancaDeDia();
  obterConfigDoSupabase();

  float temperature = dht.readTemperature();
  int brightness = 0;

  if (!isnan(temperature)) {
    brightness = calcularBrilho(tempMin, tempMax, temperature);
    light.setBrightness(brightness);

    enviarDadosSupabase(temperature, brightness);

    if (millis() - tempoUltimaTela >= intervaloTela) {
      tempoUltimaTela = millis();
      atualizarLCD(temperature, brightness);
    }

  } else {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sensor erro!");
    Serial.println("Falha ao ler o sensor DHT!");
  }

  delay(2000);
}
