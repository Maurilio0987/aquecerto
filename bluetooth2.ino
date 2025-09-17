// ======================================================================
// BIBLIOTECAS (EXISTENTES + BLE + MBEDTLS)
// ======================================================================
#include <DHT.h>
#include <dimmable_light.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>
#include <WiFi.h>
#include <time.h>
#include <SPIFFS.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include "mbedtls/base64.h"
#include <esp_task_wdt.h>

// ======================================================================
// DEFINIÇÕES E PINOS (EXISTENTES)
// ======================================================================
#define WDT_TIMEOUT 8

#define Sensor1 4
#define Sensor2 15
#define Sensor3 34
#define Sensor4 35

#define DHTTYPE DHT11
#define LIGHT_PIN 12
#define Z_C_PIN 5
#define RELE_PIN 14

// ======================================================================
// DEFINIÇÕES BLE (EXISTENTES)
// ======================================================================
#define SERVICE_UUID        "c55a5538-3141-4c54-a038-164516a858e7"
#define CHARACTERISTIC_UUID "2d0c657e-616a-4c28-936b-1663a8a38b1f"

// ======================================================================
// OBJETOS E VARIÁVEIS GLOBAIS
// ======================================================================
DHT dht1(Sensor1, DHTTYPE);
DHT dht2(Sensor2, DHTTYPE);
//DHT dht3(Sensor3, DHTTYPE);
//DHT dht4(Sensor4, DHTTYPE);

DimmableLight light(LIGHT_PIN);
LiquidCrystal_I2C lcd(0x27, 20, 4);

String ssid;
String password;

// ... (resto das variáveis globais sem alteração)
float semana1_tempMax = 35.0;
float semana1_tempMin = 33.0;
float semana2_tempMax = 34.0;
float semana2_tempMin = 32.0;
unsigned long intervaloVerificacao = 60000 * 0.5;
unsigned long ultimoTempoVerificacao = 0;
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -3 * 3600;
const int daylightOffset_sec = 0;
const char* supabaseUrl = "https://rktybanymktqkjyopcrd.supabase.co/rest/v1/campanulas";
const char* supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJrdHliYW55bWt0cWtqeW9wY3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzNzIxMjcsImV4cCI6MjA2Njk0ODEyN30.8bUcaM1MdjcuWoMsbqaDFoBM4YDY8p5nXfkMRNgjEz0";
const char *code = "/codigo.txt";
const char *config = "/config.txt";
const char *wifi_config = "/wifi_config.json";
unsigned long tempoUltimaTela = 0;
const unsigned long intervaloTela = 3000;
int estadoDisplay = 0;
String ultimaData = "";
String codigo;
float tempMax;
float tempMin;
int dia;
int estadoRele = 0;
int ultimoMinutoEnvio = -1;
bool wifiConectado = false;
unsigned long ultimoTempoWiFi = 0;
const unsigned long intervaloWiFi = 10000;


// ======================================================================
// DECLARAÇÃO DAS FUNÇÕES
// ======================================================================
void salvarConfig(const char* arquivo);

// ======================================================================
// FUNÇÃO LCD (EXISTENTE)
// ======================================================================
void exibirMensagemLCD(String msg, int linha, int tempo) {
  lcd.clear();
  lcd.setCursor(0, linha);
  lcd.print(msg);
  delay(tempo);
}

// ======================================================================
// CLASSE DE CALLBACK BLE - CORRIGIDA COM DECODIFICAÇÃO BASE64
// ======================================================================
class MyCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    Serial.println("--- onWrite callback ACIONADO! ---");

    std::string receivedBase64 = pCharacteristic->getValue();

    if (receivedBase64.length() > 0) {
      Serial.print("Dado recebido (Base64): ");
      Serial.println(receivedBase64.c_str());

      // --- PASSO DE DECODIFICAÇÃO BASE64 ---
      size_t output_len;
      mbedtls_base64_decode(NULL, 0, &output_len, (const unsigned char *)receivedBase64.c_str(), receivedBase64.length());
      
      unsigned char* decoded_json_bytes = (unsigned char*)malloc(output_len + 1);
      if (decoded_json_bytes == NULL) {
          Serial.println("Falha ao alocar memoria para decodificacao!");
          return;
      }

      int ret = mbedtls_base64_decode(decoded_json_bytes, output_len + 1, &output_len, (const unsigned char *)receivedBase64.c_str(), receivedBase64.length());
      
      if (ret != 0) {
        Serial.println("Falha ao decodificar Base64!");
        free(decoded_json_bytes);
        return;
      }
      
      decoded_json_bytes[output_len] = '\0'; 
      
      Serial.print("Dado decodificado (JSON): ");
      Serial.println((char*)decoded_json_bytes);
      // --- FIM DO PASSO DE DECODIFICAÇÃO ---

      bool needsRestart = false;
      StaticJsonDocument<256> newConfigDoc;
      
      DeserializationError error = deserializeJson(newConfigDoc, (char*)decoded_json_bytes);
      
      free(decoded_json_bytes); 

      if (error) {
        Serial.print("Falha ao parsear JSON: ");
        Serial.println(error.c_str());
        exibirMensagemLCD("Erro no formato!", 1, 2000);
        return;
      }

      // --- O RESTO DA SUA LÓGICA PERMANECE IGUAL ---
      if (newConfigDoc.containsKey("ssid") || newConfigDoc.containsKey("pass")) {
        File file = SPIFFS.open(wifi_config, "r");
        StaticJsonDocument<200> wifiDoc;
        if (file) {
          deserializeJson(wifiDoc, file);
          file.close();
        }
        if (newConfigDoc.containsKey("ssid")) {
          wifiDoc["ssid"] = newConfigDoc["ssid"].as<String>();
          Serial.println("SSID atualizado.");
        }
        if (newConfigDoc.containsKey("pass")) {
          wifiDoc["pass"] = newConfigDoc["pass"].as<String>();
          Serial.println("Senha atualizada.");
        }
        file = SPIFFS.open(wifi_config, "w");
        if (file) {
          serializeJson(wifiDoc, file);
          file.close();
          Serial.println("Configuracao WiFi salva!");
          needsRestart = true;
        } else {
          Serial.println("Erro ao salvar config WiFi.");
        }
      }
      
      if (newConfigDoc.containsKey("dia")) {
        dia = newConfigDoc["dia"];
        salvarConfig(config);
        Serial.print("Dia atualizado para: ");
        Serial.println(dia);
        needsRestart = true;
      }

      if (needsRestart) {
        exibirMensagemLCD("Configurado! ", 1, 1500);
        exibirMensagemLCD("Reiniciando...", 1, 2000);
        ESP.restart();
      }
    } else {
      Serial.println("onWrite acionado, mas o valor recebido estava vazio.");
    }
  }
};

// ======================================================================
// FUNÇÃO CARREGAR WIFI - MODIFICADA PARA NÃO TER VALORES PADRÃO
// ======================================================================
void carregarConfigWiFi() {
  if (SPIFFS.exists(wifi_config)) {
    File file = SPIFFS.open(wifi_config, "r");
    if (file) {
      StaticJsonDocument<200> doc;
      if (deserializeJson(doc, file) == DeserializationError::Ok) {
        ssid = doc["ssid"].as<String>();
        password = doc["pass"].as<String>();
        Serial.println("Configuracao WiFi carregada.");
      } else {
        Serial.println("Erro ao ler JSON do WiFi. Credenciais vazias.");
        ssid = "";
        password = "";
      }
      file.close();
    }
  } else {
    Serial.println("Arquivo de config WiFi nao encontrado. Credenciais vazias.");
    ssid = "";
    password = "";
  }
}

// ... (Restante do seu código original, sem alterações) ...
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

void atualizarLCD(float temperatura, float s1, float s2, int brilho) {
  int percent = map(brilho, 0, 255, 0, 100);
  
  lcd.clear();

  if (estadoDisplay == 0) {
    lcd.setCursor(0, 0);
    lcd.print("Codigo:");
    lcd.print(codigo);

    lcd.print(" Dia:");
    lcd.print(dia);

    lcd.setCursor(0, 1);
    lcd.print("S1: ");
    if (isnan(s1)) {
      lcd.print("Erro");
    } else {
      lcd.print(s1, 1);
    }
    lcd.print(" S2: ");
    if (isnan(s2)) {
      lcd.print("Erro");
    } else {
      lcd.print(s2, 1);
    }

    lcd.setCursor(0, 2);
    lcd.print("Temp media: ");
    if (isnan(temperatura)) {
      lcd.print("Erro");
    } else {
      lcd.print(temperatura, 1);
    }
    
    lcd.setCursor(0, 3);
    lcd.print("Aquecimento: ");
    lcd.print(percent);
    lcd.print(" %");
  } else if (estadoDisplay == 1) {
    lcd.setCursor(0, 0);
    lcd.print("Codigo:");
    lcd.print(codigo);

    lcd.print(" Dia:");
    lcd.print(dia);

    lcd.setCursor(0, 1);
    lcd.print("S1: ");
    if (isnan(s1)) {
      lcd.print("Erro");
    } else {
      lcd.print(s1, 1);
    }
    lcd.print(" S2: ");
    if (isnan(s2)) {
      lcd.print("Erro");
    } else {
      lcd.print(s2, 1);
    }

    lcd.setCursor(0, 2);
    lcd.print("Temp media: ");
    if (isnan(temperatura)) {
      lcd.print("Erro");
    } else {
      lcd.print(temperatura, 1);
    }

    lcd.setCursor(0, 3);
    lcd.print("Aquecimento: ");
    lcd.print(percent);
    lcd.print(" %");
  }
  estadoDisplay = (estadoDisplay + 1) % 2;
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
  if (!SPIFFS.exists(arquivo)) {
    Serial.println("Arquivo de configuração não encontrado. Usando valores padrão.");
    dia = 0;
    ultimaData = obterDataAtual();
    salvarConfig(arquivo);
    return;
  }

  File file = SPIFFS.open(arquivo, "r");
  if (!file) {
    Serial.println("Erro ao abrir o arquivo de configuração. Usando valores padrão.");
    dia = 0;
    ultimaData = obterDataAtual();
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError erro = deserializeJson(doc, file);
  file.close();

  if (erro) {
    Serial.println("Erro ao carregar JSON. Usando valores padrão.");
    dia = 0;
    ultimaData = obterDataAtual();
    return;
  }

  dia = doc["dia"] | 0; // Se 'dia' não existir, o padrão será 0
  ultimaData = doc["ultimaData"] | obterDataAtual();
}

void salvarConfig(const char* arquivo) {
  StaticJsonDocument<512> doc;
  doc["dia"] = dia;
  doc["ultimaData"] = ultimaData;
  File file = SPIFFS.open(arquivo, "w");
  if (file) {
    serializeJson(doc, file);
    file.close();
  }
}

float definirTempMaxima(int dia) {
  return (dia < 7) ? semana1_tempMax : semana2_tempMax;
}

float definirTempMinima(int dia) {
  return (dia < 7) ? semana1_tempMin : semana2_tempMin;
}

void atualizarConfigComBaseNoDia() {
  tempMax = definirTempMaxima(dia);
  tempMin = definirTempMinima(dia);
  salvarConfig(config);
}

void enviarDadosSupabase(float temperatura, int brilho, float umidade, int estadoRele) {
  if (!wifiConectado) return;

  StaticJsonDocument<256> doc;
  JsonArray data = doc.to<JsonArray>();
  JsonObject item = data.createNestedObject();
  item["id"] = codigo;
  item["temp_atual"] = temperatura;
  item["intensidade"] = map(brilho, 0, 255, 0, 100);
  item["umidade"] = umidade;
  item["dia"] = dia;
  item["temp_max"] = tempMax;
  item["temp_min"] = tempMin;
  item["refrigeracao"] = estadoRele;

  time_t now;
  struct tm timeinfo;
  time(&now);
  localtime_r(&now, &timeinfo);

  if ((timeinfo.tm_min == 0 || timeinfo.tm_min == 30) && timeinfo.tm_min != ultimoMinutoEnvio) {
    ultimoMinutoEnvio = timeinfo.tm_min;
    StaticJsonDocument<256> leituraDoc;
    leituraDoc["campanula_id"] = codigo;
    leituraDoc["temperatura"] = temperatura;
    leituraDoc["umidade"] = umidade;
    leituraDoc["intensidade"] = map(brilho, 0, 255, 0, 100);

    String leituraPayload;
    serializeJson(leituraDoc, leituraPayload);

    HTTPClient leituraHttp;
    leituraHttp.begin("https://rktybanymktqkjyopcrd.supabase.co/rest/v1/leituras_sensores");
    leituraHttp.addHeader("Content-Type", "application/json");
    leituraHttp.addHeader("apikey", supabaseKey);
    leituraHttp.addHeader("Authorization", "Bearer " + String(supabaseKey));
    leituraHttp.addHeader("Prefer", "return=representation");

    int leituraCode = leituraHttp.POST(leituraPayload);
    if (leituraCode > 0) {
      Serial.printf("[Supabase - leituras_sensores] Código de resposta: %d\n", leituraCode);
      String resposta = leituraHttp.getString();
      Serial.println("Resposta: " + resposta);
    } else {
      Serial.printf("[Supabase - leituras_sensores] Erro: %s\n", leituraHttp.errorToString(leituraCode).c_str());
    }
    leituraHttp.end();

    time_t limite = now - 86400;
    char timestamp[30];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", gmtime(&limite));

    String urlExclusao = "https://rktybanymktqkjyopcrd.supabase.co/rest/v1/leituras_sensores";
    urlExclusao += "?campanula_id=eq." + codigo;
    urlExclusao += "&created_at=lt." + String(timestamp);

    HTTPClient deleteHttp;
    deleteHttp.begin(urlExclusao);
    deleteHttp.addHeader("apikey", supabaseKey);
    deleteHttp.addHeader("Authorization", "Bearer " + String(supabaseKey));
    int deleteCode = deleteHttp.sendRequest("DELETE");

    if (deleteCode > 0) {
      Serial.printf("[Supabase - deletar antigos] Código de resposta: %d\n", deleteCode);
    } else {
      Serial.printf("[Supabase - deletar antigos] Erro: %s\n", deleteHttp.errorToString(deleteCode).c_str());
    }
    deleteHttp.end();
  }

  HTTPClient http;
  http.begin(supabaseUrl);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("apikey", supabaseKey);
  http.addHeader("Authorization", "Bearer " + String(supabaseKey));
  http.addHeader("Prefer", "resolution=merge-duplicates");

  String jsonPayload;
  serializeJson(doc, jsonPayload);
  Serial.println("Enviando para o Supabase: " + jsonPayload);

  int httpCode = http.POST(jsonPayload);
  if (httpCode > 0) {
    Serial.printf("[Supabase] Código de resposta: %d\n", httpCode);
  } else {
    Serial.printf("[Supabase] Erro: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
}


int calcularDiferencaDias(String dataInicial, String dataFinal) {
  int anoI, mesI, diaI;
  int anoF, mesF, diaF;

  if (sscanf(dataInicial.c_str(), "%d-%d-%d", &anoI, &mesI, &diaI) != 3 ||
      sscanf(dataFinal.c_str(), "%d-%d-%d", &anoF, &mesF, &diaF) != 3) {
    return 0;
  }

  struct tm tmInicial = {0};
  struct tm tmFinal = {0};

  tmInicial.tm_year = anoI - 1900;
  tmInicial.tm_mon = mesI - 1;
  tmInicial.tm_mday = diaI;

  tmFinal.tm_year = anoF - 1900;
  tmFinal.tm_mon = mesF - 1;
  tmFinal.tm_mday = diaF;

  time_t tInicial = mktime(&tmInicial);
  time_t tFinal = mktime(&tmFinal);

  if (tInicial == -1 || tFinal == -1) return 0;

  double segundos = difftime(tFinal, tInicial);
  int dias = round(segundos / 86400.0);
  return max(dias, 0);
}


void verificarMudancaDeDia() {
  String dataAtual = obterDataAtual();
  if (dataAtual != "" && dataAtual != ultimaData) {
    int diferenca = calcularDiferencaDias(ultimaData, dataAtual);
    dia += diferenca;
    ultimaData = dataAtual;
    atualizarConfigComBaseNoDia();
    salvarConfig(config);
  }
}

void tentarReconectarWiFi() {
  if (ssid.length() == 0 || password.length() == 0) {
    if (wifiConectado) Serial.println("Credenciais WiFi invalidas. Desconectando.");
    wifiConectado = false;
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConectado) {
      wifiConectado = true;
      Serial.println("[WiFi] Conectado.");
      configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    }
    return;
  }

  if (millis() - ultimoTempoWiFi >= intervaloWiFi) {
    ultimoTempoWiFi = millis();
    Serial.println("[WiFi] Tentando conectar...");
    WiFi.begin(ssid.c_str(), password.c_str());
  }

  wifiConectado = false;
}

void exibirConteudoArquivo(const char* caminho) {
  if (!SPIFFS.exists(caminho)) {
    Serial.printf("Arquivo %s não encontrado!\n", caminho);
    return;
  }

  File file = SPIFFS.open(caminho, "r");
  if (!file) {
    Serial.printf("Erro ao abrir o arquivo %s\n", caminho);
    return;
  }

  Serial.printf("Conteúdo de %s:\n", caminho);
  while (file.available()) {
    Serial.write(file.read());
  }
  file.close();
  Serial.println();
}

// ======================================================================
// FUNÇÃO SETUP - ATUALIZADA
// ======================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Inicializando o Watchdog Timer...");
  esp_task_wdt_init(WDT_TIMEOUT, true); // Habilita o pânico (reset) em caso de timeout
  esp_task_wdt_add(NULL);
  Serial.println("Watchdog Timer inicializado.");

  lcd.init();
  lcd.backlight();
  
  if (!SPIFFS.begin(true)) {
    Serial.println("Erro ao montar SPIFFS");
    exibirMensagemLCD("Erro SPIFFS!", 1, 5000);
    return;
  }
  
  codigo = carregarCodigo(code);
  
  carregarConfigWiFi();
  carregarConfig(config);

  // --- INICIALIZA O BLUETOOTH COM O NOME DINÂMICO ---
  BLEDevice::init(codigo.c_str());
  BLEServer *pServer = BLEDevice::createServer();
  BLEService *pService = pServer->createService(SERVICE_UUID);
  
  // --- ALTERAÇÃO CRÍTICA: ADICIONA AS PROPRIEDADES DE ESCRITA ---
  BLECharacteristic *pCharacteristic = pService->createCharacteristic(
                                         CHARACTERISTIC_UUID,
                                         BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR // <-- Propriedades atualizadas
                                       );
                                       
  pCharacteristic->setCallbacks(new MyCallbacks());
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();
  Serial.println("Servidor BLE de configuracao iniciado.");
  Serial.print("Nome do dispositivo BLE: ");
  Serial.println(codigo);
  
  // --- INICIALIZA O RESTANTE DOS COMPONENTES ---
  dht1.begin();
  dht2.begin();
  //dht3.begin();
  //dht4.begin();
  pinMode(RELE_PIN, OUTPUT);
  DimmableLight::setSyncPin(Z_C_PIN);
  DimmableLight::begin();
  
  if (ssid.length() > 0 && password.length() > 0) {
    WiFi.begin(ssid.c_str(), password.c_str());
  }
  ultimoTempoWiFi = millis() - intervaloWiFi;
  
  exibirConteudoArquivo(config);
  atualizarConfigComBaseNoDia();
  digitalWrite(RELE_PIN, HIGH);
  estadoRele = 0;
}

// ======================================================================
// FUNÇÃO LOOP (SEM ALTERAÇÕES)
// ======================================================================
void loop() {
  esp_task_wdt_reset();
  
  tentarReconectarWiFi();
  float temperatura1 = dht1.readTemperature();
  float umidade1 = dht1.readHumidity();
  float temperatura2 = dht2.readTemperature();
  float umidade2 = dht2.readHumidity();

  int brilho = 0;
  float tsoma = 0;
  float tdivisao = 0;
  float temperatura;
  float umidade;

  if (!isnan(temperatura1)) {
    tsoma += temperatura1;
    tdivisao += 1;
  } else {
    temperatura1 = NAN;
  }
  if (!isnan(temperatura2)) {
    tsoma += temperatura2;
    tdivisao += 1;
  } else {
    temperatura2 = NAN;
  }

  if (tdivisao >= 1) {
    temperatura = tsoma / tdivisao;  
  } else {
    temperatura = NAN;
  }

  float usoma = 0;
  float udivisao = 0;
  if (!isnan(umidade1)) {
    usoma += umidade1;
    udivisao += 1;
  }
  if (!isnan(umidade2)) {
    usoma += umidade2;
    udivisao += 1;
  }

  if (udivisao >= 1) {
    umidade = usoma / udivisao;  
  } else {
    umidade = NAN;
  }
  
  if (!isnan(temperatura) && !isnan(umidade)) {
    brilho = calcularBrilho(tempMin, tempMax, temperatura);
    light.setBrightness(brilho);

    if (temperatura >= tempMax) {
      digitalWrite(RELE_PIN, LOW);
      estadoRele = 1;
    } else if (temperatura <= tempMin) {
      digitalWrite(RELE_PIN, HIGH);
      estadoRele = 0;
    }

    enviarDadosSupabase(temperatura, brilho, umidade, estadoRele);
    if (millis() - tempoUltimaTela >= intervaloTela) {
      tempoUltimaTela = millis();
      atualizarLCD(temperatura, temperatura1, temperatura2, brilho);
    }
  } else {
    brilho = 0;
    atualizarLCD(temperatura, temperatura1, temperatura2, brilho);
    Serial.println("Erro na leitura do DHT");
  }

  unsigned long tempoAtual = millis();
  if (WiFi.status() == WL_CONNECTED && tempoAtual - ultimoTempoVerificacao >= intervaloVerificacao) {
    ultimoTempoVerificacao = tempoAtual;
    verificarMudancaDeDia();
    enviarDadosSupabase(temperatura, brilho, umidade, estadoRele);
    Serial.println("verificado");
  }

  delay(2000);
}
