import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

// Mock the create campaign screen with a simplified version for testing
class CreateCampaignFormTest extends StatefulWidget {
  const CreateCampaignFormTest({super.key});

  @override
  State<CreateCampaignFormTest> createState() => _CreateCampaignFormTestState();
}

class _CreateCampaignFormTestState extends State<CreateCampaignFormTest> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _hashtagController = TextEditingController();
  final List<String> _hashtags = [];

  void _addHashtag() {
    var tag = _hashtagController.text.trim();
    if (tag.isEmpty) return;
    if (!tag.startsWith('#')) tag = '#$tag';
    tag = tag.replaceAll(' ', '');
    if (!_hashtags.contains(tag)) {
      setState(() {
        _hashtags.add(tag);
        _hashtagController.clear();
      });
    }
  }

  void _removeHashtag(String tag) {
    setState(() => _hashtags.remove(tag));
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextFormField(
              key: const Key('title_field'),
              controller: _titleController,
              decoration: const InputDecoration(labelText: 'Campaign Title'),
              validator: (value) =>
                  value == null || value.isEmpty ? 'Required' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('description_field'),
              controller: _descriptionController,
              decoration: const InputDecoration(labelText: 'Description'),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    key: const Key('hashtag_input'),
                    controller: _hashtagController,
                    decoration: const InputDecoration(hintText: '#hashtag'),
                  ),
                ),
                IconButton(
                  key: const Key('add_hashtag_button'),
                  icon: const Icon(Icons.add),
                  onPressed: _addHashtag,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _hashtags
                  .map((tag) => Chip(
                        key: Key('hashtag_chip_$tag'),
                        label: Text(tag),
                        onDeleted: () => _removeHashtag(tag),
                      ))
                  .toList(),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              key: const Key('generate_button'),
              onPressed: () {
                if (_formKey.currentState!.validate()) {
                  // Submit form
                }
              },
              child: const Text('Generate Drafts'),
            ),
          ],
        ),
      ),
    );
  }
}

void main() {
  group('CreateCampaignForm', () {
    Widget createTestWidget() {
      return ProviderScope(
        child: MaterialApp(
          home: const Scaffold(
            body: CreateCampaignFormTest(),
          ),
        ),
      );
    }

    testWidgets('renders all form fields', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Check that all fields are rendered
      expect(find.byKey(const Key('title_field')), findsOneWidget);
      expect(find.byKey(const Key('description_field')), findsOneWidget);
      expect(find.byKey(const Key('hashtag_input')), findsOneWidget);
      expect(find.byKey(const Key('add_hashtag_button')), findsOneWidget);
      expect(find.byKey(const Key('generate_button')), findsOneWidget);
    });

    testWidgets('accepts title input', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Enter text in title field
      await tester.enterText(
        find.byKey(const Key('title_field')),
        'Test Campaign',
      );
      await tester.pump();

      // Verify the text was entered
      expect(find.text('Test Campaign'), findsOneWidget);
    });

    testWidgets('accepts description input', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Enter text in description field
      await tester.enterText(
        find.byKey(const Key('description_field')),
        'This is a test description',
      );
      await tester.pump();

      expect(find.text('This is a test description'), findsOneWidget);
    });

    testWidgets('adds hashtags with # prefix', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Enter hashtag without #
      await tester.enterText(
        find.byKey(const Key('hashtag_input')),
        'TestTag',
      );
      await tester.pump();

      // Click add button
      await tester.tap(find.byKey(const Key('add_hashtag_button')));
      await tester.pump();

      // Verify hashtag chip was created with #
      expect(find.byKey(const Key('hashtag_chip_#TestTag')), findsOneWidget);
      expect(find.text('#TestTag'), findsOneWidget);
    });

    testWidgets('adds hashtags that already have # prefix',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Enter hashtag with #
      await tester.enterText(
        find.byKey(const Key('hashtag_input')),
        '#AlreadyHasHash',
      );
      await tester.pump();

      // Click add button
      await tester.tap(find.byKey(const Key('add_hashtag_button')));
      await tester.pump();

      // Verify hashtag chip was created
      expect(
        find.byKey(const Key('hashtag_chip_#AlreadyHasHash')),
        findsOneWidget,
      );
    });

    testWidgets('removes hashtags when delete is tapped',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Add a hashtag
      await tester.enterText(
        find.byKey(const Key('hashtag_input')),
        '#ToRemove',
      );
      await tester.tap(find.byKey(const Key('add_hashtag_button')));
      await tester.pump();

      // Verify it exists
      expect(find.byKey(const Key('hashtag_chip_#ToRemove')), findsOneWidget);

      // Find and tap the delete icon on the chip
      final chipFinder = find.byKey(const Key('hashtag_chip_#ToRemove'));
      final chip = tester.widget<Chip>(chipFinder);
      expect(chip.onDeleted, isNotNull);

      // Tap somewhere to trigger delete (delete icons in Chip)
      await tester.tap(find.descendant(
        of: chipFinder,
        matching: find.byIcon(Icons.cancel),
      ));
      await tester.pump();

      // Verify it was removed
      expect(find.byKey(const Key('hashtag_chip_#ToRemove')), findsNothing);
    });

    testWidgets('validates required title field', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Tap generate button without entering title
      await tester.tap(find.byKey(const Key('generate_button')));
      await tester.pump();

      // Validation error should appear
      expect(find.text('Required'), findsOneWidget);
    });

    testWidgets('form is valid when title is provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // Enter title
      await tester.enterText(
        find.byKey(const Key('title_field')),
        'Valid Title',
      );
      await tester.pump();

      // Tap generate button
      await tester.tap(find.byKey(const Key('generate_button')));
      await tester.pump();

      // No validation error should appear
      expect(find.text('Required'), findsNothing);
    });
  });
}
