import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'dashboard_tab.dart';
import 'search_tab.dart';
import 'settings_tab.dart';
import 'vault_tab.dart';

class MainShell extends StatefulWidget {
  final int initialIndex;

  const MainShell({super.key, this.initialIndex = 0});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  late int _currentIndex;
  final GlobalKey<State<SearchTab>> _searchTabKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
  }

  void _onSearchRequestedFromHome(String query) {
    setState(() {
      _currentIndex = 1; // Switch to Search tab
    });
    // Trigger query on Search tab
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final searchState = _searchTabKey.currentState as dynamic;
      if (searchState != null && searchState.setQueryAndSearch != null) {
        searchState.setQueryAndSearch(query);
      }
    });
  }

  void _onViewAllFromHome() {
    setState(() {
      _currentIndex = 2; // Switch to Vault tab
    });
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      DashboardTab(
        onSearchRequested: _onSearchRequestedFromHome,
        onViewAllDocuments: _onViewAllFromHome,
      ),
      SearchTab(key: _searchTabKey),
      const VaultTab(),
      const SettingsTab(),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: tabs,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(
            top: BorderSide(color: AppTheme.border, width: 1),
          ),
          boxShadow: [
            BoxShadow(
              color: Color(0x0A000000),
              blurRadius: 10,
              offset: Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          backgroundColor: Colors.white,
          selectedItemColor: AppTheme.primary,
          unselectedItemColor: const Color(0xFF94A3B8),
          selectedFontSize: 11.5,
          unselectedFontSize: 11,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500),
          type: BottomNavigationBarType.fixed,
          elevation: 0,
          items: const [
            BottomNavigationBarItem(
              icon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.home_rounded, size: 24),
              ),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.search_rounded, size: 24),
              ),
              label: 'Search',
            ),
            BottomNavigationBarItem(
              icon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.folder_copy_outlined, size: 22),
              ),
              activeIcon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.folder_copy_rounded, size: 22),
              ),
              label: 'Vault',
            ),
            BottomNavigationBarItem(
              icon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.settings_outlined, size: 22),
              ),
              activeIcon: Padding(
                padding: EdgeInsets.only(bottom: 3),
                child: Icon(Icons.settings_rounded, size: 22),
              ),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
