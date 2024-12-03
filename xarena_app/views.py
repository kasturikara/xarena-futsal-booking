from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView , DetailView, ListView
from django.http import HttpResponseNotAllowed, JsonResponse
from django.core.paginator import Paginator
from .models import CustomUser, Lapangan, Jadwal, Pemesanan
from .forms import CustomUserCreationForm, CustomAuthenticationForm


# tampilan register
def register_view(request):
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Akun berhasil dibuat untuk {user.username}. Silakan login.')
            return redirect('login')
        else:
            for msg in form.error_messages:
                messages.error(request, f'{msg}: {form.error_messages[msg]}')
    else:
        form = CustomUserCreationForm()

    return render(request, 'auth/register.html', {'form': form})

# tampilan login
def login_view(request):
    if request.user.is_authenticated:
        return redirect('landing')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Selamat datang kembali, {username}.')
                
                # Redirect based on user type
                if user.is_superuser:
                    return redirect('dashboard_admin')
                elif user.is_staff:
                    return redirect('dashboard_staff')
                else:
                    return redirect('dashboard_user')
            else:
                messages.error(request, 'Username atau password tidak valid.')
                form.add_error(None, 'Username atau password tidak valid.')
        else:
            messages.error(request, 'Username atau password tidak valid.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})
    
# tampilan logout
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Anda telah keluar.')
        return redirect('landing')
    return render(request, 'auth/logout.html')


def landing(request):
    return render(request, "public/landing.html",)


def about(request):
    return render(request, "public/about.html",)


# -----USER-----
@login_required
def dashboard_user(request):
    if request.user.is_staff or request.user.is_superuser:
        raise PermissionDenied
    
    pemesanan = Pemesanan.objects.filter(
        user=request.user
    ).select_related(
        'jadwal',
        'jadwal__lapangan'
    ).order_by('-created_at')
    
    total = sum(pesan.hitung_harga() for pesan in pemesanan)
    
    context = {
        'pemesanan': pemesanan,
        'total': total,
        'pending_bookings': pemesanan.filter(status='pending').count(),
        'completed_bookings': pemesanan.filter(status='selesai').count()
    }
    
    return render(request, 'user/dashboard_user.html', context)

# list lapangan
class LapanganListView(ListView):
    model = Lapangan
    template_name = 'public/list_lapangan.html'
    context_object_name = 'lapangan'
    
    def get_queryset(self):
        return Lapangan.objects.all()
        # return Lapangan.objects.all().filter(is_available=True)

# detail lapangan
class DetailLapanganView(LoginRequiredMixin, DetailView):
    model = Lapangan
    template_name = 'user/detail_lapangan.html'
    pk_url_kwarg = 'lapangan_id'
    context_object_name = 'lapangan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dates = []
        
        # Get all unique dates from Jadwal
        jadwal_dates = Jadwal.objects.filter(
            lapangan=self.object,
            # is_available=True
        ).dates('tanggal', 'day')

        for date in jadwal_dates:
            jadwal = Jadwal.objects.filter(
                lapangan=self.object,
                tanggal=date,
                # is_available=True
            )
            dates.append({
                'date': date,
                'slots': jadwal
            })
            
        context['dates'] = dates
        return context

# pesan lapangan
class PemesananCreateView(LoginRequiredMixin, CreateView):
    model = Pemesanan
    template_name = "user/konfirmasi_pemesanan.html"
    fields = ['metode_pembayaran']
    success_url = reverse_lazy('dashboard_user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jadwal = get_object_or_404(Jadwal, id=self.kwargs['jadwal_id'])

        # buat temp pemesanan untuk hitung harga
        temp_pemesanan = Pemesanan(jadwal=jadwal)
        harga = temp_pemesanan.hitung_harga()

        context.update({
            'jadwal': jadwal,
            'lapangan': jadwal.lapangan,
            'harga': harga
        })
        return context
    
    def form_valid(self, form):
        jadwal = get_object_or_404(Jadwal, id=self.kwargs['jadwal_id'])
        if not jadwal.is_available:
            messages.error(self.request, 'Jadwal tidak tersedia.')
            return self.form_invalid(form)

        form.instance.user = self.request.user
        form.instance.jadwal = jadwal
        jadwal.is_available = False
        jadwal.save()
        
        messages.success(self.request, 'Pemesanan berhasil dibuat.')
        return super().form_valid(form)

# cancel pesanan
@login_required
def cancel_pemesanan(request, pemesanan_id):
    pemesanan = get_object_or_404(Pemesanan, id=pemesanan_id, user=request.user)
    
    # Only allow cancellation of pending orders
    if pemesanan.status != 'pending':
        messages.error(request, 'Hanya pemesanan dengan status pending yang dapat dibatalkan.')
        return redirect('dashboard_user')
        
    if request.method == 'POST':
        # Update pemesanan status
        pemesanan.status = 'dibatalkan'
        pemesanan.save()
        
        # Make jadwal available again
        jadwal = pemesanan.jadwal
        jadwal.is_available = True 
        jadwal.save()
        
        messages.success(request, 'Pemesanan berhasil dibatalkan.')
        return redirect('dashboard_user')
        
    return render(request, 'user/konfirmasi_cancel_pemesanan.html', {'pemesanan': pemesanan})



# -----STAFF-----
@staff_member_required
def dashboard_staff(request):
    pemesanan_list = Pemesanan.objects.all().order_by('-created_at')
    paginator = Paginator(pemesanan_list, 10)
    
    users = CustomUser.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by('username')
    
    lapangan = Lapangan.objects.all()

    page = request.GET.get('page')
    pemesanan = paginator.get_page(page)
    
    context = {
        'pemesanan': pemesanan,
        'users': users,
        'lapangan': lapangan,
        'total_pemesanan': pemesanan_list.count(),
        'pending_pemesanan': pemesanan_list.filter(status='pending').count(),
        'diterima_pemesanan': pemesanan_list.filter(status='diterima').count(),
        'completed_pemesanan': pemesanan_list.filter(status='selesai').count(),
    }
    
    return render(request, 'staff/dashboard_staff.html', context)

# detail pemesanan untuk staff
@staff_member_required 
def detail_pemesanan_staff(request, pk):
    pemesanan = get_object_or_404(Pemesanan, pk=pk)
    return render(request, 'staff/detail_pemesanan_staff.html', {
        'pemesanan': pemesanan
    })

# update status pemesanan
@login_required
def update_pemesanan(request, pk):
    if not request.user.is_staff or request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        pemesanan = get_object_or_404(Pemesanan, pk=pk)
        status = request.POST.get('status')
        
        if status in ['dibatalkan', 'pending', 'diterima', 'selesai']:
            pemesanan.status = status
            pemesanan.staff = request.user
            pemesanan.save()
            messages.success(request, f'Status pemesanan oleh {pemesanan.user.username} berhasil diubah menjadi {status}.')
        else:
            messages.error(request, 'Status tidak valid')
            
        return redirect('dashboard_staff')
        
    return HttpResponseNotAllowed(['POST'])

# ambil jadwal tersedia
@login_required
def get_available_jadwal(request):
    lapangan_id = request.GET.get('lapangan')
    tanggal = request.GET.get('tanggal')
    
    if not lapangan_id or not tanggal:
        return JsonResponse([], safe=False)
    
    jadwal = Jadwal.objects.filter(
        lapangan_id=lapangan_id,
        tanggal=tanggal,
        is_available=True
    ).values('id', 'jam_mulai', 'jam_selesai')
    
    return JsonResponse(list(jadwal), safe=False)

# add pemesanan
@login_required
def add_pemesanan(request):
    if not request.user.is_staff or request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == 'POST':
        user_id = request.POST.get('user')
        jadwal_id = request.POST.get('jadwal')
        metode_pembayaran = request.POST.get('metode_pembayaran')
        
        user = get_object_or_404(CustomUser, id=user_id, is_staff=False, is_superuser=False)
        jadwal = get_object_or_404(Jadwal, id=jadwal_id)
        
        if not jadwal.is_available:
            messages.error(request, 'Jadwal tidak tersedia.')
            return redirect('dashboard_staff')
        
        pemesanan = Pemesanan.objects.create(
            user=user,
            jadwal=jadwal,
            metode_pembayaran=metode_pembayaran,
            status='diterima',
            staff=request.user
        )
        
        jadwal.is_available = False
        jadwal.save()
        
        messages.success(request, f'Pemesanan oleh {user.username} berhasil dibuat.')
        return redirect('dashboard_staff')
    
    return HttpResponseNotAllowed(['POST'])
    
# -----ADMIN-----
@login_required
def dashboard_admin(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    # Example data for admin dashboard
    pemesanan = Pemesanan.objects.all()
    total_pemesanan = pemesanan.count()
    pending_pemesanan = pemesanan.filter(status='pending').count()
    completed_pemesanan = pemesanan.filter(status='selesai').count()
    total_users = CustomUser.objects.count()
    total_staff = CustomUser.objects.filter(is_staff=True).count()

    context = {
        'pemesanan': pemesanan,
        'total_pemesanan': total_pemesanan,
        'pending_pemesanan': pending_pemesanan,
        'completed_pemesanan': completed_pemesanan,
        'total_users': total_users,
        'total_staff': total_staff,
    }
    
    return render(request, 'admin/dashboard_admin.html', context)