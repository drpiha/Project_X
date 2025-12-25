import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/auth/screens/welcome_screen.dart';
import '../../features/campaigns/screens/campaign_list_screen.dart';
import '../../features/campaigns/screens/create_campaign_screen.dart';
import '../../features/drafts/screens/draft_review_screen.dart';
import '../../features/settings/screens/settings_screen.dart';
import '../../features/logs/screens/logs_screen.dart';
import '../../providers/providers.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    debugLogDiagnostics: true,
    routes: [
      GoRoute(
        path: '/',
        name: 'welcome',
        builder: (context, state) => const WelcomeScreen(),
      ),
      GoRoute(
        path: '/campaigns',
        name: 'campaigns',
        builder: (context, state) => const CampaignListScreen(),
        routes: [
          GoRoute(
            path: 'create',
            name: 'create-campaign',
            builder: (context, state) => const CreateCampaignScreen(),
          ),
          GoRoute(
            path: ':id/drafts',
            name: 'draft-review',
            builder: (context, state) {
              final campaignId = state.pathParameters['id']!;
              return DraftReviewScreen(campaignId: campaignId);
            },
          ),
        ],
      ),
      GoRoute(
        path: '/settings',
        name: 'settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/logs',
        name: 'logs',
        builder: (context, state) => const LogsScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Text('Page not found: ${state.uri}'),
      ),
    ),
  );
});
