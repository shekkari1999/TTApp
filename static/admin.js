/**
 * Admin Setup Page JavaScript
 * Handles CRUD operations for teachers, subjects, and classes
 */

// Navigation functionality
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-section]');
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.getAttribute('data-section');
            showSection(sectionId);
            
            // Update active nav item
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
        
        // Load data for the section if needed
        if (sectionId === 'all-users') {
            loadAllUsers();
        } else if (sectionId === 'pending-users') {
            loadPendingUsers();
        } else if (sectionId === 'teachers') {
            loadTeachers();
        } else if (sectionId === 'subjects') {
            loadSubjects();
        } else if (sectionId === 'classes') {
            loadClasses();
        } else if (sectionId === 'class-teachers') {
            showClassTeachersOverview();
        } else if (sectionId === 'schedule') {
            loadSchedule();
        } else if (sectionId === 'absent-teachers') {
            loadAbsentTeachers();
        }
    }
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    // Load initial data for active section
    loadPendingUsers();
    loadAllUsers();
    loadTeachers();
    loadSubjects();
    loadClasses();
});

/**
 * PENDING USERS MANAGEMENT
 */
async function loadPendingUsers() {
    try {
        const response = await fetch('/api/pending-users');
        const data = await response.json();
        
        if (data.success) {
            displayPendingUsers(data.users);
        }
    } catch (error) {
        console.error('Error loading pending users:', error);
        document.getElementById('pendingUsersList').innerHTML = 
            '<p style="color: var(--text-secondary);">Error loading pending users.</p>';
    }
}

function displayPendingUsers(users) {
    const container = document.getElementById('pendingUsersList');
    
    if (users.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No pending user requests.</p></div>';
        return;
    }
    
    container.innerHTML = `
        <div class="data-list">
            ${users.map(user => `
                <div class="data-card">
                    <div class="data-card-info">
                        <div class="data-card-name">
                            ${user.username}
                            <span class="badge" style="background: #fbbf24; color: #78350f; margin-left: 8px;">Pending</span>
                        </div>
                        <div class="data-card-meta">Email: ${user.email}</div>
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-primary" onclick="approveUser(${user.id})" style="font-size: 0.8125rem;">Approve</button>
                        <button class="btn btn-secondary" onclick="rejectUser(${user.id})" style="font-size: 0.8125rem;">Reject</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function approveUser(userId) {
    // Get user info to pre-fill form
    try {
        const pendingUsers = await fetch('/api/pending-users').then(r => r.json());
        const user = pendingUsers.users?.find(u => u.id === userId);
        
        // Show modal to optionally create teacher profile
        document.getElementById('approveUserId').value = userId;
        if (user) {
            document.getElementById('teacherName').value = user.username; // Pre-fill with username
        }
        document.getElementById('approveUserModal').style.display = 'flex';
        
        // Load subjects for selection
        await loadSubjectsForApproval();
    } catch (error) {
        console.error('Error loading user info:', error);
        document.getElementById('approveUserId').value = userId;
        document.getElementById('approveUserModal').style.display = 'flex';
        await loadSubjectsForApproval();
    }
}

function toggleTeacherFields() {
    const createProfile = document.getElementById('createTeacherProfile').checked;
    const teacherFields = document.getElementById('teacherFields');
    teacherFields.style.display = createProfile ? 'block' : 'none';
    
    // Make teacher name required only if creating profile
    document.getElementById('teacherName').required = createProfile;
    
    // Reset class teacher checkbox when toggling
    if (!createProfile) {
        document.getElementById('teacherIsClassTeacher').checked = false;
        toggleClassTeacherFields();
    }
}

function toggleClassTeacherFields() {
    const isClassTeacher = document.getElementById('teacherIsClassTeacher').checked;
    const classTeacherFields = document.getElementById('classTeacherFields');
    const classSelect = document.getElementById('teacherClassId');
    
    classTeacherFields.style.display = isClassTeacher ? 'block' : 'none';
    classSelect.required = isClassTeacher;
    
    if (!isClassTeacher) {
        classSelect.value = '';
    }
}

async function loadSubjectsForApproval() {
    try {
        const [subjectsResponse, classesResponse] = await Promise.all([
            fetch('/api/subjects'),
            fetch('/api/classes')
        ]);
        
        const subjectsData = await subjectsResponse.json();
        const classesData = await classesResponse.json();
        
        const subjectsSelect = document.getElementById('teacherSubjects');
        const classesSelect = document.getElementById('teacherClassId');
        
        // Load subjects into dropdown
        if (subjectsData.success && subjectsData.subjects.length > 0) {
            subjectsSelect.innerHTML = subjectsData.subjects.map(subject => 
                `<option value="${subject.id}">${subject.name}</option>`
            ).join('');
        } else {
            subjectsSelect.innerHTML = '<option value="">No subjects available. Please add subjects first.</option>';
        }
        
        // Load classes into dropdown
        if (classesData.success && classesData.classes.length > 0) {
            // Clear the default option and add classes
            classesSelect.innerHTML = '<option value="">Select a class...</option>';
            classesData.classes.forEach(cls => {
                const option = document.createElement('option');
                option.value = cls.id;
                option.textContent = cls.name;
                classesSelect.appendChild(option);
            });
        } else {
            classesSelect.innerHTML = '<option value="">No classes available. Please add classes first.</option>';
        }
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('teacherSubjects').innerHTML = 
            '<option value="">Error loading subjects</option>';
        document.getElementById('teacherClassId').innerHTML = 
            '<option value="">Error loading classes</option>';
    }
}

async function submitApproveUser(event) {
    event.preventDefault();
    
    const userId = document.getElementById('approveUserId').value;
    const createTeacher = document.getElementById('createTeacherProfile').checked;
    
    const approveData = {
        create_teacher: createTeacher
    };
    
    if (createTeacher) {
        approveData.teacher_name = document.getElementById('teacherName').value;
        const isClassTeacher = document.getElementById('teacherIsClassTeacher').checked;
        approveData.is_class_teacher = isClassTeacher;
        
        // Get selected subject IDs from dropdown
        const subjectsSelect = document.getElementById('teacherSubjects');
        const selectedSubjects = Array.from(subjectsSelect.selectedOptions)
            .map(option => parseInt(option.value))
            .filter(id => !isNaN(id));
        approveData.subject_ids = selectedSubjects;
        
        // Get selected class if class teacher
        if (isClassTeacher) {
            const classId = document.getElementById('teacherClassId').value;
            if (classId) {
                approveData.class_id = parseInt(classId);
            }
        }
    }
    
    try {
        const response = await fetch(`/api/users/${userId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(approveData)
        });
        
        const data = await response.json();
        if (data.success) {
            alert(data.message || 'User approved successfully!');
            closeModal('approveUserModal');
            loadPendingUsers();
            loadAllUsers();
            if (createTeacher) {
                loadTeachers(); // Refresh teachers list
            }
        } else {
            alert('Error: ' + (data.message || 'Failed to approve user'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function rejectUser(userId) {
    if (!confirm('Are you sure you want to reject this user? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${userId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            alert('User rejected.');
            loadPendingUsers();
            loadAllUsers();
        } else {
            alert('Error: ' + (data.message || 'Failed to reject user'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * ALL USERS MANAGEMENT
 */
async function loadAllUsers() {
    try {
        const response = await fetch('/api/users');
        const data = await response.json();
        
        if (data.success) {
            await displayAllUsers(data.users);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('allUsersList').innerHTML = 
            '<div class="empty-state"><p>Error loading users.</p></div>';
    }
}

async function displayAllUsers(users) {
    const container = document.getElementById('allUsersList');
    
    if (users.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No users found.</p></div>';
        return;
    }
    
    // Get current user ID
    let currentUserId = null;
    try {
        const authResponse = await fetch('/api/auth/check');
        const authData = await authResponse.json();
        if (authData.success && authData.authenticated) {
            currentUserId = authData.current_user_id;
        }
    } catch (error) {
        console.error('Error getting current user:', error);
    }
    
    container.innerHTML = `
        <div class="data-list">
            ${users.map(user => {
                const statusBadge = {
                    'pending': { bg: '#fbbf24', color: '#78350f', text: 'Pending' },
                    'approved': { bg: '#10b981', color: '#065f46', text: 'Approved' },
                    'rejected': { bg: '#ef4444', color: '#991b1b', text: 'Rejected' }
                }[user.status] || { bg: '#6b7280', color: '#1f2937', text: user.status };
                
                const isAdmin = user.is_admin ? '<span class="badge" style="background: #4f46e5; color: white; margin-left: 8px;">Admin</span>' : '';
                const isCurrentUser = user.id === currentUserId;
                
                return `
                    <div class="data-card">
                        <div class="data-card-info">
                            <div class="data-card-name">
                                ${user.username}
                                ${isAdmin}
                                <span class="badge" style="background: ${statusBadge.bg}; color: ${statusBadge.color}; margin-left: 8px;">${statusBadge.text}</span>
                            </div>
                            <div class="data-card-meta">
                                Email: ${user.email}
                                ${user.teacher_id ? ' | Linked to Teacher' : ''}
                            </div>
                        </div>
                        <div class="data-card-actions">
                            ${!isCurrentUser ? `<button class="btn btn-icon-only btn-delete" onclick="deleteUser(${user.id})" title="Delete">🗑️</button>` : '<span style="color: #999; font-size: 0.75rem;">Current User</span>'}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This will also delete their associated teacher profile if one exists. This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            alert(data.message || 'User deleted successfully.');
            loadAllUsers();
            loadPendingUsers();
            loadTeachers();
            loadClasses();
        } else {
            alert('Error: ' + (data.message || 'Failed to delete user'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * TEACHERS MANAGEMENT
 */
async function loadTeachers() {
    try {
        const response = await fetch('/api/teachers');
        const data = await response.json();
        
        if (data.success) {
            displayTeachers(data.teachers);
        }
    } catch (error) {
        console.error('Error loading teachers:', error);
    }
}

function displayTeachers(teachers) {
    const container = document.getElementById('teachersList');
    
    if (teachers.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No teachers added yet. Click "Add Teacher" to get started.</p></div>';
        return;
    }
    
    container.innerHTML = `
        <div class="data-list">
            ${teachers.map(teacher => `
                <div class="data-card">
                    <div class="data-card-info">
                        <div class="data-card-name">
                            ${teacher.name}
                            ${teacher.is_class_teacher ? '<span class="badge badge-class-teacher">Class Teacher</span>' : ''}
                            ${teacher.is_leisure ? '<span class="badge badge-leisure">Leisure</span>' : ''}
                        </div>
                        <div class="data-card-meta">ID: ${teacher.id}</div>
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-icon-only" onclick="editTeacher(${teacher.id})" title="Edit">✏️</button>
                        <button class="btn btn-icon-only btn-delete" onclick="deleteTeacher(${teacher.id})" title="Delete">🗑️</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function showAddTeacherForm() {
    document.getElementById('teacherModalTitle').textContent = 'Add Teacher';
    document.getElementById('teacherForm').reset();
    document.getElementById('teacherId').value = '';
    document.getElementById('teacherIsClassTeacherModal').checked = false;
    
    // Enable username/email fields for new teacher
    document.getElementById('teacherUsernameModal').disabled = false;
    document.getElementById('teacherEmailModal').disabled = false;
    
    toggleClassTeacherFieldsModal();
    
    // Load subjects and classes for dropdowns
    await loadSubjectsAndClassesForTeacherModal();
    
    document.getElementById('teacherModal').style.display = 'flex';
}

function toggleClassTeacherFieldsModal() {
    const isClassTeacher = document.getElementById('teacherIsClassTeacherModal').checked;
    const classTeacherFields = document.getElementById('classTeacherFieldsModal');
    const classSelect = document.getElementById('teacherClassIdModal');
    
    classTeacherFields.style.display = isClassTeacher ? 'block' : 'none';
    classSelect.required = isClassTeacher;
    
    if (!isClassTeacher) {
        classSelect.value = '';
    }
}

async function loadSubjectsAndClassesForTeacherModal() {
    try {
        const [subjectsResponse, classesResponse] = await Promise.all([
            fetch('/api/subjects'),
            fetch('/api/classes')
        ]);
        
        const subjectsData = await subjectsResponse.json();
        const classesData = await classesResponse.json();
        
        const subjectsSelect = document.getElementById('teacherSubjectsModal');
        const classesSelect = document.getElementById('teacherClassIdModal');
        
        // Load subjects into dropdown
        if (subjectsData.success && subjectsData.subjects.length > 0) {
            subjectsSelect.innerHTML = subjectsData.subjects.map(subject => 
                `<option value="${subject.id}">${subject.name}</option>`
            ).join('');
        } else {
            subjectsSelect.innerHTML = '<option value="">No subjects available. Please add subjects first.</option>';
        }
        
        // Load classes into dropdown
        if (classesData.success && classesData.classes.length > 0) {
            // Clear the default option and add classes
            classesSelect.innerHTML = '<option value="">Select a class...</option>';
            classesData.classes.forEach(cls => {
                const option = document.createElement('option');
                option.value = cls.id;
                option.textContent = cls.name;
                classesSelect.appendChild(option);
            });
        } else {
            classesSelect.innerHTML = '<option value="">No classes available. Please add classes first.</option>';
        }
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('teacherSubjectsModal').innerHTML = 
            '<option value="">Error loading subjects</option>';
        document.getElementById('teacherClassIdModal').innerHTML = 
            '<option value="">Error loading classes</option>';
    }
}

async function editTeacher(id) {
    try {
        const [teachersResponse, teacherSubjectsResponse, usersResponse] = await Promise.all([
            fetch('/api/teachers'),
            fetch(`/api/teachers/${id}/subjects`),
            fetch('/api/users')
        ]);
        
        const teachersData = await teachersResponse.json();
        const subjectsData = await teacherSubjectsResponse.json();
        const usersData = await usersResponse.json();
        
        const teacher = teachersData.teachers.find(t => t.id === id);
        
        if (teacher) {
            document.getElementById('teacherModalTitle').textContent = 'Edit Teacher';
            document.getElementById('teacherId').value = teacher.id;
            document.getElementById('teacherNameModal').value = teacher.name;
            document.getElementById('teacherIsClassTeacherModal').checked = teacher.is_class_teacher;
            
            // Find associated user and populate username/email
            const associatedUser = usersData.users?.find(u => u.teacher_id === teacher.id);
            if (associatedUser) {
                document.getElementById('teacherUsernameModal').value = associatedUser.username || '';
                document.getElementById('teacherEmailModal').value = associatedUser.email || '';
                // Disable username/email fields when editing (can't change after creation)
                document.getElementById('teacherUsernameModal').disabled = true;
                document.getElementById('teacherEmailModal').disabled = true;
            } else {
                // No user account yet - enable fields
                document.getElementById('teacherUsernameModal').disabled = false;
                document.getElementById('teacherEmailModal').disabled = false;
            }
            
            // Load subjects and classes
            await loadSubjectsAndClassesForTeacherModal();
            
            // Set selected subjects
            if (subjectsData.success && subjectsData.subjects) {
                const subjectsSelect = document.getElementById('teacherSubjectsModal');
                subjectsData.subjects.forEach(subject => {
                    const option = subjectsSelect.querySelector(`option[value="${subject.id}"]`);
                    if (option) {
                        option.selected = true;
                    }
                });
            }
            
            // Find which class this teacher is class teacher for
            if (teacher.is_class_teacher) {
                const classesResponse = await fetch('/api/classes');
                const classesData = await classesResponse.json();
                if (classesData.success) {
                    const classWithThisTeacher = classesData.classes.find(c => c.class_teacher_id === teacher.id);
                    if (classWithThisTeacher) {
                        document.getElementById('teacherClassIdModal').value = classWithThisTeacher.id;
                    }
                }
            }
            
            toggleClassTeacherFieldsModal();
            document.getElementById('teacherModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading teacher:', error);
    }
}

async function saveTeacher(event) {
    event.preventDefault();
    
    const id = document.getElementById('teacherId').value;
    const isClassTeacher = document.getElementById('teacherIsClassTeacherModal').checked;
    
    const teacherData = {
        name: document.getElementById('teacherNameModal').value,
        is_class_teacher: isClassTeacher,
        is_leisure: false  // Removed from UI, always false
    };
    
    // Get username and email for user account creation (only when creating new teacher)
    if (!id) {
        const username = document.getElementById('teacherUsernameModal').value.trim();
        const email = document.getElementById('teacherEmailModal').value.trim();
        
        // Only require username when creating new teacher (email is optional)
        if (!username) {
            alert('Username is required when creating a new teacher.');
            return;
        }
        teacherData.username = username;
        teacherData.email = email || null;  // Email is optional, can be empty
    }
    
    // Get selected subject IDs from dropdown
    const subjectsSelect = document.getElementById('teacherSubjectsModal');
    const selectedSubjects = Array.from(subjectsSelect.selectedOptions)
        .map(option => parseInt(option.value))
        .filter(val => !isNaN(val));
    teacherData.subject_ids = selectedSubjects;
    
    // Get selected class if class teacher
    if (isClassTeacher) {
        const classId = document.getElementById('teacherClassIdModal').value;
        if (classId) {
            teacherData.class_id = parseInt(classId);
        }
    }
    
    try {
        let response;
        if (id) {
            // Update
            response = await fetch(`/api/teachers/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(teacherData)
            });
        } else {
            // Create
            response = await fetch('/api/teachers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(teacherData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('teacherModal');
            loadTeachers();
            loadClasses(); // Reload classes in case class teacher changed
        } else {
            alert('Error: ' + (data.message || 'Failed to save teacher'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteTeacher(id) {
    if (!confirm('Are you sure you want to delete this teacher?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/teachers/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadTeachers();
            loadClasses(); // Reload classes in case class teacher was deleted
        } else {
            alert('Error: ' + (data.message || 'Failed to delete teacher'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * SUBJECTS MANAGEMENT
 */
async function loadSubjects() {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();
        
        if (data.success) {
            displaySubjects(data.subjects);
        }
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

function displaySubjects(subjects) {
    const container = document.getElementById('subjectsList');
    
    if (subjects.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No subjects added yet. Click "Add Subject" to get started.</p></div>';
        return;
    }
    
    container.innerHTML = `
        <div class="data-list">
            ${subjects.map(subject => `
                <div class="data-card">
                    <div class="data-card-info">
                        <div class="data-card-name">${subject.name}</div>
                        <div class="data-card-meta">ID: ${subject.id}</div>
                    </div>
                    <div class="data-card-actions">
                        <button class="btn btn-icon-only" onclick="editSubject(${subject.id})" title="Edit">✏️</button>
                        <button class="btn btn-icon-only btn-delete" onclick="deleteSubject(${subject.id})" title="Delete">🗑️</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function showAddSubjectForm() {
    document.getElementById('subjectModalTitle').textContent = 'Add Subject';
    document.getElementById('subjectForm').reset();
    document.getElementById('subjectId').value = '';
    document.getElementById('subjectModal').style.display = 'flex';
}

async function resetSubjects() {
    if (!confirm('This will delete all subjects and reset their IDs.\n\nIt will only proceed if no timetables or teachers are using any subjects.\n\nAre you sure you want to continue?')) {
        return;
    }

    try {
        const response = await fetch('/api/subjects/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.success) {
            alert(data.message || 'Subjects reset successfully.');
            loadSubjects();
        } else {
            alert(data.message || 'Cannot reset subjects. They might be referenced by teachers or timetables.');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * TEACHERS RESET (ID MANAGEMENT)
 */
async function resetTeachers() {
    if (!confirm('This will delete all teachers and reset their IDs.\n\nIt will only proceed if no classes, users, timetables, or absences are using any teachers.\n\nAre you sure you want to continue?')) {
        return;
    }

    try {
        const response = await fetch('/api/teachers/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.success) {
            alert(data.message || 'Teachers reset successfully.');
            loadTeachers();
            loadClasses(); // classes may lose class_teacher_id
        } else {
            alert(data.message || 'Cannot reset teachers. They might be referenced.');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * CLASSES RESET (ID MANAGEMENT)
 */
async function resetClasses() {
    if (!confirm('This will delete all classes and reset their IDs.\n\nIt will only proceed if no timetables are using any classes.\n\nAre you sure you want to continue?')) {
        return;
    }

    try {
        const response = await fetch('/api/classes/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.success) {
            alert(data.message || 'Classes reset successfully.');
            loadClasses();
            loadTeachers(); // teachers may lose class_teacher_id references
        } else {
            alert(data.message || 'Cannot reset classes. They might be referenced by timetables.');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * CLASS TEACHERS OVERVIEW
 */
async function showClassTeachersOverview() {
    const container = document.getElementById('classTeachersOverview');
    container.innerHTML = '<p class="class-teachers-loading">Loading class teachers...</p>';
    
    try {
        const [classesRes, teachersRes] = await Promise.all([
            fetch('/api/classes'),
            fetch('/api/teachers')
        ]);
        const classesData = await classesRes.json();
        const teachersData = await teachersRes.json();
        
        if (!classesData.success || !teachersData.success) {
            container.innerHTML = '<p class="class-teachers-empty">Error loading class/teacher data.</p>';
            return;
        }
        
        const teachers = teachersData.teachers || [];
        const teacherMap = {};
        teachers.forEach(t => { teacherMap[t.id] = t; });
        
        const classes = classesData.classes || [];
        if (classes.length === 0) {
            container.innerHTML = '<p class="class-teachers-empty">No classes found.</p>';
            return;
        }
        
        // Sort classes by name for better organization
        classes.sort((a, b) => a.name.localeCompare(b.name));
        
        // Render as a simple table
        const rowsHtml = classes.map(cls => {
            const teacher = cls.class_teacher_id ? teacherMap[cls.class_teacher_id] : null;
            const teacherName = teacher ? teacher.name : '—';
            const teacherNote = teacher && teacher.is_class_teacher ? 'Class Teacher' : (teacher ? '' : 'No teacher assigned');
            
            return `
                <tr>
                    <td>${cls.name}</td>
                    <td>${teacherName}</td>
                    <td>${teacherNote}</td>
                </tr>
            `;
        }).join('');
        
        container.innerHTML = `
            <table class="class-teachers-table">
                <thead>
                    <tr>
                        <th>Class</th>
                        <th>Teacher</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Error loading class teachers overview:', error);
        container.innerHTML = '<p class="class-teachers-empty">Unable to load class teachers overview. Please try again.</p>';
    }
}

async function editSubject(id) {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();
        const subject = data.subjects.find(s => s.id === id);
        
        if (subject) {
            document.getElementById('subjectModalTitle').textContent = 'Edit Subject';
            document.getElementById('subjectId').value = subject.id;
            document.getElementById('subjectName').value = subject.name;
            document.getElementById('subjectModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading subject:', error);
    }
}

async function saveSubject(event) {
    event.preventDefault();
    
    const id = document.getElementById('subjectId').value;
    const subjectData = {
        name: document.getElementById('subjectName').value
    };
    
    try {
        let response;
        if (id) {
            response = await fetch(`/api/subjects/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subjectData)
            });
        } else {
            response = await fetch('/api/subjects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subjectData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('subjectModal');
            loadSubjects();
        } else {
            alert('Error: ' + (data.message || 'Failed to save subject'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteSubject(id) {
    if (!confirm('Are you sure you want to delete this subject?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/subjects/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadSubjects();
        } else {
            alert('Error: ' + (data.message || 'Failed to delete subject'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * CLASSES MANAGEMENT
 */
async function loadClasses() {
    try {
        const response = await fetch('/api/classes');
        const data = await response.json();
        
        if (data.success) {
            displayClasses(data.classes);
            populateClassTeacherSelect(data.classes);
        }
    } catch (error) {
        console.error('Error loading classes:', error);
    }
}

async function populateClassTeacherSelect(classes) {
    // Load teachers for the select dropdown
    const teachersResponse = await fetch('/api/teachers');
    const teachersData = await teachersResponse.json();
    
    const select = document.getElementById('classTeacherId');
    select.innerHTML = '<option value="">None</option>';
    
    if (teachersData.success) {
        teachersData.teachers.forEach(teacher => {
            const option = document.createElement('option');
            option.value = teacher.id;
            option.textContent = teacher.name;
            select.appendChild(option);
        });
    }
}

function displayClasses(classes) {
    const container = document.getElementById('classesList');
    
    if (classes.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No classes added yet. Click "Add Class" to get started.</p></div>';
        return;
    }
    
    // Load teachers to get names
    fetch('/api/teachers')
        .then(r => r.json())
        .then(data => {
            const teachers = data.teachers || [];
            const teacherMap = {};
            teachers.forEach(t => teacherMap[t.id] = t.name);
            
            container.innerHTML = `
                <div class="data-list">
                    ${classes.map(classObj => `
                        <div class="data-card">
                            <div class="data-card-info">
                                <div class="data-card-name">${classObj.name}</div>
                                <div class="data-card-meta">
                                    ${classObj.class_teacher_id ? `Class Teacher: ${teacherMap[classObj.class_teacher_id] || 'Unknown'}` : 'No class teacher assigned'}
                                </div>
                            </div>
                            <div class="data-card-actions">
                                <button class="btn btn-icon-only" onclick="editClass(${classObj.id})" title="Edit">✏️</button>
                                <button class="btn btn-icon-only btn-delete" onclick="deleteClass(${classObj.id})" title="Delete">🗑️</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        });
}

function showAddClassForm() {
    document.getElementById('classModalTitle').textContent = 'Add Class';
    document.getElementById('classForm').reset();
    document.getElementById('classId').value = '';
    populateClassTeacherSelect([]);
    document.getElementById('classModal').style.display = 'flex';
}

async function editClass(id) {
    try {
        const response = await fetch('/api/classes');
        const data = await response.json();
        const classObj = data.classes.find(c => c.id === id);
        
        if (classObj) {
            document.getElementById('classModalTitle').textContent = 'Edit Class';
            document.getElementById('classId').value = classObj.id;
            document.getElementById('className').value = classObj.name;
            await populateClassTeacherSelect([]);
            document.getElementById('classTeacherId').value = classObj.class_teacher_id || '';
            document.getElementById('classModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading class:', error);
    }
}

async function saveClass(event) {
    event.preventDefault();
    
    const id = document.getElementById('classId').value;
    const classData = {
        name: document.getElementById('className').value,
        class_teacher_id: document.getElementById('classTeacherId').value || null
    };
    
    try {
        let response;
        if (id) {
            response = await fetch(`/api/classes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(classData)
            });
        } else {
            response = await fetch('/api/classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(classData)
            });
        }
        
        const data = await response.json();
        if (data.success) {
            closeModal('classModal');
            loadClasses();
        } else {
            alert('Error: ' + (data.message || 'Failed to save class'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteClass(id) {
    if (!confirm('Are you sure you want to delete this class?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classes/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            loadClasses();
        } else {
            alert('Error: ' + (data.message || 'Failed to delete class'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * MODAL MANAGEMENT
 */
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = ['teacherModal', 'subjectModal', 'classModal', 'approveUserModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            closeModal(modalId);
        }
    });
}

