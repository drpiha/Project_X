import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/app_config.dart';

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiBaseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      'Content-Type': 'application/json',
    },
  ));

  dio.interceptors.add(LogInterceptor(
    requestBody: true,
    responseBody: true,
    error: true,
  ));

  return dio;
});

class ApiClient {
  final Dio _dio;
  String? _userId;

  ApiClient(this._dio);

  void setUserId(String userId) {
    _userId = userId;
  }

  String? get userId => _userId;

  Map<String, dynamic> get _headers => {
    if (_userId != null) 'X-User-Id': _userId!,
  };

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return _dio.get<T>(
      path,
      queryParameters: queryParameters,
      options: Options(headers: _headers),
    );
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(headers: _headers),
    );
  }

  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
  }) async {
    return _dio.put<T>(
      path,
      data: data,
      options: Options(headers: _headers),
    );
  }

  Future<Response<T>> delete<T>(String path) async {
    return _dio.delete<T>(
      path,
      options: Options(headers: _headers),
    );
  }

  Future<Response<T>> postMultipart<T>(
    String path, {
    required FormData formData,
  }) async {
    return _dio.post<T>(
      path,
      data: formData,
      options: Options(
        headers: {
          ..._headers,
          'Content-Type': 'multipart/form-data',
        },
      ),
    );
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  final dio = ref.watch(dioProvider);
  return ApiClient(dio);
});
