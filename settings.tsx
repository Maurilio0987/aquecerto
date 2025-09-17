import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
  ActivityIndicator,
  TextInput,
  Platform, // Para verificar o sistema operacional
  PermissionsAndroid, // Para pedir permissão no Android
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArrowLeft, Bluetooth, Send, WifiOff, CheckCircle2 } from 'lucide-react-native';
import { router } from 'expo-router';
import { BleManager, Device } from 'react-native-ble-plx';
import { encode } from 'base-64';

// UUIDs do seu ESP32
const SERVICE_UUID = "c55a5538-3141-4c54-a038-164516a858e7";
const CHARACTERISTIC_UUID = "2d0c657e-616a-4c28-936b-1663a8a38b1f";

export default function BleConfigScreen() {
  // Inicializa o BleManager. useMemo garante que seja criado apenas uma vez.
  const bleManager = useMemo(() => new BleManager(), []);

  const [device, setDevice] = useState<Device | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Aguardando ação...');
  const [jsonString, setJsonString] = useState('{"ssid": "", "pass": ""}');

  // Função para solicitar as permissões necessárias de Bluetooth
  const requestBluetoothPermission = async (): Promise<boolean> => {
    // No iOS a solicitação de permissão é tratada automaticamente pelo sistema
    if (Platform.OS === 'ios') {
      return true;
    }

    // Para Android 12 (API 31) ou superior, precisamos de BLUETOOTH_SCAN e BLUETOOTH_CONNECT
    if (Platform.OS === 'android' && Platform.Version >= 31) {
      const result = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
      ]);

      const isScanGranted = result[PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN] === PermissionsAndroid.RESULTS.GRANTED;
      const isConnectGranted = result[PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT] === PermissionsAndroid.RESULTS.GRANTED;

      return isScanGranted && isConnectGranted;
    }

    // Para Android 11 (API 30) ou inferior, precisamos de ACCESS_FINE_LOCATION
    if (Platform.OS === 'android' && Platform.Version < 31) {
      const result = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      );
      return result === PermissionsAndroid.RESULTS.GRANTED;
    }

    // Retorna falso como padrão se nenhuma das condições for atendida
    return false;
  };

  // Roda na montagem do componente para pedir a permissão e limpar recursos ao sair
  useEffect(() => {
    requestBluetoothPermission().then(granted => {
      if (granted) {
        console.log('Permissões de Bluetooth concedidas.');
      } else {
        Alert.alert('Permissão Negada', 'O aplicativo precisa de permissões de Bluetooth para funcionar corretamente.');
      }
    });

    return () => {
      bleManager.destroy();
    };
  }, [bleManager]);


  // Função para procurar o ESP32
  const scanForDevice = async () => {
    const isPermissionGranted = await requestBluetoothPermission();
    if (!isPermissionGranted) {
      Alert.alert('Permissão Necessária', 'Por favor, conceda as permissões de Bluetooth nas configurações do seu celular para procurar dispositivos.');
      return;
    }

    bleManager.state().then(state => {
      if (state !== 'PoweredOn') {
        Alert.alert('Bluetooth Desligado', 'Por favor, ative o Bluetooth para continuar.');
        return;
      }

      setIsScanning(true);
      setStatusMessage('Procurando dispositivo...');
      setDevice(null);
      setIsConnected(false);

      bleManager.startDeviceScan([SERVICE_UUID], null, (error, scannedDevice) => {
        if (error) {
          console.error('Erro ao escanear:', error);
          setStatusMessage(`Erro: ${error.message}`);
          setIsScanning(false);
          return;
        }

        if (scannedDevice) {
          console.log('Dispositivo encontrado:', scannedDevice.name);
          bleManager.stopDeviceScan();
          setIsScanning(false);
          setDevice(scannedDevice);
          connectToDevice(scannedDevice);
        }
      });

      setTimeout(() => {
        if (isScanning) {
          bleManager.stopDeviceScan();
          setIsScanning(false);
          setStatusMessage('Nenhum dispositivo encontrado. Tente novamente.');
        }
      }, 10000);
    });
  };

  // Função para conectar ao dispositivo encontrado
  const connectToDevice = async (deviceToConnect: Device) => {
    try {
      setStatusMessage(`Conectando a ${deviceToConnect.name || 'dispositivo'}...`);
      const connectedDevice = await deviceToConnect.connect();
      setStatusMessage(`Conectado a ${connectedDevice.name}!`);
      setIsConnected(true);

      await connectedDevice.discoverAllServicesAndCharacteristics();
      console.log('Serviços e características descobertos.');

    } catch (error) {
      console.error('Falha ao conectar:', error);
      setStatusMessage(`Falha ao conectar.`);
      setIsConnected(false);
      setDevice(null);
    }
  };

  // Função para enviar o JSON para o ESP32
  const sendJsonData = async () => {
    if (!isConnected || !device) {
      Alert.alert('Erro', 'Nenhum dispositivo conectado.');
      return;
    }

    try {
      JSON.parse(jsonString);
    } catch (error) {
      Alert.alert('JSON Inválido', 'A string digitada não é um formato JSON válido.');
      return;
    }

    setIsSending(true);
    setStatusMessage('Enviando dados...');

    try {
      const base64Data = encode(jsonString);
      console.log(`Enviando dados (Base64): ${base64Data}`);

      await bleManager.writeCharacteristicWithResponseForDevice(
        device.id,
        SERVICE_UUID,
        CHARACTERISTIC_UUID,
        base64Data
      );

      Alert.alert('Sucesso!', 'Dados enviados para a campânula.');
      setStatusMessage(`Dados enviados com sucesso para ${device.name}!`);

    } catch (error) {
      console.error('Erro ao enviar dados:', error);
      Alert.alert('Erro', 'Não foi possível enviar os dados.');
      setStatusMessage('Erro ao enviar.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <ArrowLeft size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.title}>Configuração BLE</Text>
            <Text style={styles.subtitle}>Conecte e envie dados para a campânula</Text>
          </View>
        </View>

        <ScrollView style={styles.content} keyboardShouldPersistTaps="handled">

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>1. Conectar ao Dispositivo</Text>
            <TouchableOpacity 
              style={[styles.actionButton, isScanning && styles.actionButtonDisabled]} 
              onPress={scanForDevice}
              disabled={isScanning}
            >
              {isScanning ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Bluetooth size={20} color="#fff" />
              )}
              <Text style={styles.actionButtonText}>
                {isScanning ? 'Procurando...' : 'Procurar Dispositivo'}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.statusContainer}>
              {isConnected ? <CheckCircle2 size={20} color="#4ade80" /> : <WifiOff size={20} color="#ef4444" />}
              <Text style={[styles.statusText, {color: isConnected ? '#4ade80' : '#ef4444'}]}>
                Status: {isConnected ? `Conectado a ${device?.name}` : 'Desconectado'}
              </Text>
          </View>
          <Text style={styles.statusMessageText}>{statusMessage}</Text>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>2. Enviar Configuração (JSON)</Text>
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                multiline
                placeholder='Ex: {"ssid": "nome-da-rede", "pass": "senha123"}'
                placeholderTextColor="#6b7280"
                value={jsonString}
                onChangeText={setJsonString}
                autoCapitalize="none"
                keyboardAppearance="dark"
              />
            </View>
            <TouchableOpacity 
              style={[styles.actionButton, styles.sendButton, (!isConnected || isSending) && styles.actionButtonDisabled]}
              onPress={sendJsonData}
              disabled={!isConnected || isSending}
            >
              {isSending ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Send size={20} color="#fff" />
              )}
              <Text style={styles.actionButtonText}>
                {isSending ? 'Enviando...' : 'Enviar Dados'}
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

// Estilos
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  safeArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  backButton: {
    padding: 8,
    marginRight: 16,
  },
  headerInfo: {
    flex: 1,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: '#9ca3af',
    marginTop: 2,
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 24,
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  actionButton: {
    backgroundColor: '#3b82f6', // Azul
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButton: {
    backgroundColor: '#16a34a', // Verde
  },
  actionButtonDisabled: {
    backgroundColor: '#4b5563', // Cinza
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 10,
  },
  statusMessageText: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
    marginBottom: 24,
    fontStyle: 'italic',
  },
  inputContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    marginBottom: 16,
  },
  input: {
    color: '#fff',
    fontSize: 16,
    padding: 16,
    minHeight: 120,
    textAlignVertical: 'top',
  },
});
