import 'package:flutter/material.dart';

import '../models/search_result.dart';
import '../services/api_service.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _api = ApiService();
  final _controller = TextEditingController();
  List<SearchResult> _results = [];
  String? _error;
  bool _loading = false;

  Future<void> _search() async {
    final query = _controller.text.trim();
    if (query.isEmpty) {
      setState(() {
        _error = 'Enter a search word.';
        _results = [];
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await _api.search(query);
      setState(() {
        _results = response.results;
        if (response.results.isEmpty) _error = response.message.isNotEmpty ? response.message : 'No matching images found.';
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _results = [];
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SEARCH IMAGES')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: 'scholarship',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  ElevatedButton(onPressed: _search, child: const Text('SEARCH')),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView(
                      children: [
                        if (_results.isNotEmpty)
                          Text('${_results.length} Match Found',
                              style: const TextStyle(fontWeight: FontWeight.bold)),
                        ..._results.map((r) => ListTile(
                              title: Text(r.imageName),
                              subtitle: Text(r.matchedText),
                            )),
                        if (_error != null)
                          Text(_error!, style: const TextStyle(color: Colors.red)),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
